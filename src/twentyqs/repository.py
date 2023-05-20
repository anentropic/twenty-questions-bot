import random
import string
import warnings
from functools import wraps
from datetime import datetime
from typing import Sequence, Optional, List

from sqlalchemy.future import Engine
from sqlalchemy_get_or_create import get_or_create  # type: ignore
from sqlmodel import (
    Field,
    Relationship,
    Session,
    SQLModel,
    create_engine,
    select,
    JSON,
    Column,
    func,
)

from twentyqs.serde import serialize, deserialize
from twentyqs.types import JsonT, UserStats


class NotFound(Exception):
    pass


def get_code(length=8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password: str = Field(
        max_length=16,
        default_factory=get_code,
    )
    name: str
    is_admin: bool = False

    games: List["GameSession"] = Relationship(back_populates="user")


class GameSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    user: User = Relationship(back_populates="games")
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime]
    subject: str
    user_won: Optional[bool]
    llm_stats: dict | None = Field(default=None, sa_column=Column(JSON))

    turns: List["Turn"] = Relationship(back_populates="gamesession")


class Turn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gamesession_id: int = Field(foreign_key="gamesession.id", index=True)
    gamesession: GameSession = Relationship(back_populates="turns")
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime]
    question: Optional[str]
    answer: Optional[str]

    logs: List["TurnLog"] = Relationship(back_populates="turn")


class TurnLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    turn_id: int = Field(foreign_key="turn.id", index=True)
    turn: Turn = Relationship(back_populates="logs")
    timestamp: datetime = Field(default_factory=datetime.now)
    key: str
    value: dict = Field(default_factory=dict, sa_column=Column(JSON))


def with_session(f):
    """
    Will use the session passed in if given, or create a new one if none is passed.
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if "session" in kwargs or (args and isinstance(args[0], Session)):
            return f(self, *args, **kwargs)
        with Session(self.engine) as session:
            return f(self, session, *args, **kwargs)

    return wrapper


class Repository:
    engine: Engine

    def __init__(self, db_path: str):
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=True,
            connect_args={"check_same_thread": False},
            json_serializer=serialize,
            json_deserializer=deserialize,
        )

    def __del__(self):
        self.engine.dispose()

    def init_db(self, drop=False):
        if drop:
            SQLModel.metadata.drop_all(self.engine)
        SQLModel.metadata.create_all(self.engine)

    @with_session
    def get_or_create_user(self, session: Session, username: str) -> User:
        with session.begin_nested():
            return get_or_create(session, User, username=username)[0]

    @with_session
    def get_user_stats(self, session: Session, username: str) -> UserStats:
        """
        Return the number of games played, won and lost for a user.
        """
        query = (
            select(GameSession.user_won, func.count())  # type: ignore
            .select_from(GameSession)
            .join(User)
            .where(User.username == username)
            .group_by(GameSession.user_won)
        )
        result = dict(session.exec(query).all())
        played = sum(result.values())
        unfinished = result.get(None, 0)
        wins = result.get(True, 0)
        losses = result.get(False, 0)

        avg_query = (
            session.query(func.count(Turn.id).label("count"))
            .join(GameSession, GameSession.id == Turn.gamesession_id)
            .join(User, User.id == GameSession.user_id)
            .filter(
                User.username == username,
                GameSession.user_won.isnot(None),  # type: ignore
            )
            .group_by(GameSession.id)
        )
        overall_avg_questions = session.exec(
            func.avg(avg_query.subquery().c.count)
        ).scalar()  # type: ignore
        avg_questions_to_win = session.exec(  # type: ignore
            func.avg(avg_query.filter(GameSession.user_won is True).subquery().c.count)
        ).scalar()
        return UserStats(
            played=played,
            unfinished=unfinished,
            wins=wins,
            losses=losses,
            overall_avg_questions=overall_avg_questions,
            avg_questions_to_win=avg_questions_to_win,
        )

    @with_session
    def user_subject_history(self, session: Session, username: str) -> list[str]:
        """
        Return the history of subjects that a user has already played.
        """
        query = (
            session.query(GameSession.subject)
            .join(User)
            .filter(User.username == username)
        )
        return [subject for (subject,) in query.all()]

    @with_session
    def start_game(self, session: Session, user: User, subject: str) -> GameSession:
        """
        Start a new game for a user.
        """
        with session.begin_nested():
            game = GameSession(user=user, subject=subject)
            session.add(game)
        return game

    @with_session
    def finish_game(
        self,
        session: Session,
        game_id: int,
        user_won: bool,
        llm_stats: dict[str, JsonT] | None = None,
    ) -> None:
        """
        Finish a game.
        """
        with session.begin_nested():
            updated = (
                session.query(GameSession)
                .filter(GameSession.id == game_id)
                .update(
                    {
                        GameSession.finished_at: datetime.now(),
                        GameSession.user_won: user_won,
                        GameSession.llm_stats: llm_stats,
                    }
                )
            )
        if not updated:
            raise NotFound(GameSession, game_id)
        if updated > 1:
            warnings.warn(f"Updated {updated} rows for GameSession id:{game_id}")

    @with_session
    def start_turn(self, session: Session, game: GameSession, question: str) -> Turn:
        """
        Start a new turn for a game.
        """
        with session.begin_nested():
            turn = Turn(gamesession=game, question=question)
            session.add(turn)
        return turn

    @with_session
    def finish_turn(
        self, session: Session, turn_id: int, answer: str | None = None
    ) -> None:
        """
        Finish a turn.
        """
        with session.begin_nested():
            updated = (
                session.query(Turn)
                .filter(Turn.id == turn_id)
                .update(
                    {
                        Turn.finished_at: datetime.now(),
                        Turn.answer: answer,
                    }
                )
            )
        if not updated:
            raise NotFound(Turn, turn_id)
        if updated > 1:
            warnings.warn(f"Updated {updated} rows for Turn id:{turn_id}")

    @with_session
    def store_turn_logs(
        self, session: Session, logs: Sequence[dict[str, JsonT]]
    ) -> None:
        """
        Store the logs for a turn.
        """
        if not logs:
            return
        with session.begin_nested():
            session.bulk_insert_mappings(TurnLog, logs)
