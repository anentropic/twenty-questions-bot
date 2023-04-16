import warnings
from datetime import datetime
from typing import Collection

import peewee  # type: ignore
from playhouse.sqlite_ext import SqliteExtDatabase, JSONField  # type: ignore

from twentyqs.serde import serialize, deserialize
from twentyqs.types import JsonT, UserStats


db = SqliteExtDatabase(None)


class NotFound(Exception):
    pass


class BaseModel(peewee.Model):
    class Meta:
        database = db


class User(BaseModel):
    username = peewee.CharField(unique=True)


class GameSession(BaseModel):
    user = peewee.ForeignKeyField(User, backref='games')
    started_at = peewee.DateTimeField(default=datetime.now)
    finished_at = peewee.DateTimeField(null=True)
    subject = peewee.CharField()
    user_won = peewee.BooleanField(null=True)
    llm_stats = JSONField(serialize, deserialize, null=True)


class Turn(BaseModel):
    game = peewee.ForeignKeyField(GameSession, backref='turns')
    started_at = peewee.DateTimeField(default=datetime.now)
    finished_at = peewee.DateTimeField(null=True)
    question = peewee.CharField(null=True)
    answer = peewee.CharField(null=True)


class TurnLog(BaseModel):
    turn = peewee.ForeignKeyField(Turn, backref='logs')
    timestamp = peewee.DateTimeField(default=datetime.now)
    key = peewee.CharField()
    value = JSONField(serialize, deserialize)


MODELS = [User, GameSession, Turn, TurnLog]


def create_tables(db_name: str, drop=False):
    """
    Create the database tables.
    """
    db.init(db_name)
    with db:
        if drop:
            db.drop_tables(MODELS)
        db.create_tables(MODELS)


def get_or_create_user(username: str) -> User:
    """Create a new user."""
    user, _ =  User.get_or_create(username=username)
    return user


def get_user_stats(username: str) -> UserStats:
    """
    Return the number of games played, won and lost for a user.
    """
    query = (
        GameSession
        .select()
        .join(User)
        .where(User.username == username)
    )
    played = query.count()
    wins = query.where(GameSession.outcome == 'won').count()
    losses = query.where(GameSession.outcome == 'lost').count()

    avg_query = (
        GameSession
        .select(peewee.fn.avg(GameSession.turns.count()))
        .join(User)
        .where(
            User.username == username,
        )
    )
    overall_avg_questions = avg_query.scalar()
    avg_questions_to_win = avg_query.where(GameSession.outcome == 'won').scalar()
    return UserStats(
        played=played,
        wins=wins,
        losses=losses,
        overall_avg_questions=overall_avg_questions,
        avg_questions_to_win=avg_questions_to_win,
    )


def user_subject_history(username: str) -> list[str]:
    """
    Return the history of subjects that a user has already played.
    """
    return [
        game.subject
        for game in (
            GameSession
            .select(GameSession.subject)
            .join(User)
            .where(
                User.username == username,
                GameSession.subject.is_null(False),
            )
        )
    ]


def start_game(user: User, subject: str) -> GameSession:
    """
    Start a new game for a user.
    """
    return GameSession.create(user=user, subject=subject)


def finish_game(game_id: int, user_won: bool, llm_stats: dict[str, JsonT] | None = None) -> None:
    """
    Finish a game.
    """
    updated = GameSession.update(
        finished_at=datetime.now(),
        user_won=user_won,
        llm_stats=llm_stats,
    ).where(GameSession.id == game_id).execute()
    if not updated:
        raise NotFound(GameSession, game_id)
    if updated > 1:
        warnings.warn(f'Updated {updated} rows for GameSession id:{game_id}')


def start_turn(game: GameSession, question: str) -> Turn:
    """
    Start a new turn for a game.
    """
    return Turn.create(game=game, question=question)


def finish_turn(turn_id: int, answer: str | None = None) -> None:
    """
    Finish a turn.
    """
    updated = Turn.update(
        finished_at=datetime.now(),
        answer=answer,
    ).where(Turn.id == turn_id).execute()
    if not updated:
        raise NotFound(Turn, turn_id)
    if updated > 1:
        warnings.warn(f'Updated {updated} rows for Turn id:{turn_id}')


def store_turn_logs(logs: Collection[dict[str, JsonT]]) -> None:
    """
    Store the logs for a turn.
    """
    inserted = TurnLog.insert_many(logs).execute()
    if inserted < len(logs):
        warnings.warn(f'Inserted {inserted} rows, expected {len(logs)}')
