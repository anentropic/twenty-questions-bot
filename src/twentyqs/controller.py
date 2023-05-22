import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Protocol

from twentyqs.brain import AnswerBot
from twentyqs.repository import Repository, User, GameSession, Turn
from twentyqs.types import (
    LogKey,
    JsonT,
    TurnEndGame,
    TurnSummaryT,
    InvalidQuestionSummary,
    UserMeta,
    ValidQuestionSummary,
)

logger = logging.getLogger(__name__)


class StatsContext(Protocol):
    def get_stats(self) -> dict[str, JsonT]:
        ...


class StatsContextManager(Protocol):
    def __enter__(self) -> StatsContext:
        ...

    def __exit__(self, *args, **kwargs) -> bool | None:
        ...


StatsContextManagerFactory = Callable[..., StatsContextManager]


@dataclass(frozen=True)
class GameBegun:
    max_questions: int


@dataclass(frozen=True)
class InvalidQuestion:
    question: str
    reason: str | None


@dataclass(frozen=True)
class ContinueGame:
    questions_asked: int
    questions_remaining: int
    answer: str


@dataclass(frozen=True)
class WonGame:
    questions_asked: int
    questions_remaining: int
    answer: str


@dataclass(frozen=True)
class LostGame:
    questions_asked: int
    questions_remaining: int
    answer: str
    subject: str


TurnOutcome = InvalidQuestion | ContinueGame | WonGame | LostGame


class AuthError(Exception):
    pass


class GameController:
    answerer: AnswerBot
    require_auth: bool
    stats_context_factory: StatsContextManagerFactory | None
    _stats_context_mgr: StatsContextManager | None = None
    game_stats_context: StatsContext | None = None
    user: User
    session: GameSession | None = None
    max_questions: int
    _q_count: int = 0

    def __init__(
        self,
        repository: Repository,
        answerer: AnswerBot,
        require_auth: bool = True,
        max_questions: int = 20,
        stats_context_factory: StatsContextManagerFactory | None = None,
    ):
        self.db = repository
        self.answerer = answerer
        self.require_auth = require_auth
        self.max_questions = max_questions
        self.stats_context_factory = stats_context_factory

    def set_user(self, username: str, password: str | None) -> None:
        if self.require_auth:
            if password is None:
                raise AuthError("Authentication required")
            user = self.db.authenticated_player(username, password)
            if not user:
                raise AuthError("Invalid username/passcode")
        else:
            user = self.db.get_or_create_user(username)
        self.user = user

    def get_user_meta(self) -> UserMeta:
        if not self.user:
            raise RuntimeError("GameController: No user set")

        return UserMeta(
            username=self.user.username,
            name=self.user.name,
            stats=self.db.get_user_stats(self.user.username),
        )

    @property
    def questions_asked(self) -> int:
        """
        Valid questions asked so far.
        """
        return self._q_count

    @property
    def questions_remaining(self) -> int:
        return self.max_questions - self._q_count

    def start_game(self) -> GameBegun:
        """
        Start a new game.
        """
        if not self.user:
            raise RuntimeError("GameController: No user set")

        subject_history = self.db.get_user_subject_history(self.user.username)
        self.answerer.history = subject_history

        if self.stats_context_factory:
            self._stats_context_mgr = mgr = self.stats_context_factory()
            self.game_stats_context = mgr.__enter__()

        self.answerer.set_subject()
        self._q_count = 0
        self.session = self.db.start_game(user=self.user, subject=self.answerer.subject)
        return GameBegun(
            max_questions=self.max_questions,
        )

    def finish_game(self, user_won: bool) -> None:
        """
        Finish the current game.
        """
        assert self.session
        if self._stats_context_mgr:
            self._stats_context_mgr.__exit__(None, None, None)
            llm_stats = None
            if self.game_stats_context:
                llm_stats = self.game_stats_context.get_stats()
                logger.info("GameController.finish_game: LLM stats: %s", llm_stats)
        self.db.finish_game(self.session.id, user_won, llm_stats)

    def log_turn(self, turn: Turn, summary: TurnSummaryT) -> None:
        """
        Log a turn.
        """
        logs: list[dict[str, JsonT]] = [
            {
                "turn_id": turn.id,
                "key": LogKey.BEGIN_TURN,
                "value": asdict(summary.begin),
            },
            {
                "turn_id": turn.id,
                "key": LogKey.VALIDATE_QUESTION,
                "value": asdict(summary.validate),
            },
        ]
        if isinstance(summary, ValidQuestionSummary):
            logs.append(
                {
                    "turn_id": turn.id,
                    "key": LogKey.ANSWER_QUESTION,
                    "value": asdict(summary.answer),
                }
            )
            logs.append(
                {
                    "turn_id": turn.id,
                    "key": LogKey.IS_DECIDING_QUESTION,
                    "value": asdict(summary.end_game),
                }
            )
        self.db.store_turn_logs(logs=logs)

    def take_turn(self, question: str) -> TurnOutcome:
        """
        Take a turn in a game.
        """
        assert self.session
        turn = self.db.start_turn(
            game=self.session,
            question=question,
            questions_asked=self.questions_asked,
            questions_remaining=self.questions_remaining,
        )

        summary = self.answerer.process_turn(question)
        self.log_turn(turn=turn, summary=summary)
        if isinstance(summary, ValidQuestionSummary):
            self.db.finish_turn(turn.id, answer=summary.answer.answer)
        else:
            self.db.finish_turn(turn.id)

        outcome: TurnOutcome
        match summary:
            case InvalidQuestionSummary(begin, validate):
                outcome = InvalidQuestion(
                    question=begin.question, reason=validate.reason or ""
                )
            case ValidQuestionSummary(_, _, answer, TurnEndGame(False, _)):
                self._q_count += 1
                if self.questions_remaining == 0:
                    outcome = LostGame(
                        questions_asked=self.questions_asked,
                        questions_remaining=self.questions_remaining,
                        answer=answer.answer,
                        subject=self.session.subject,
                    )
                    self.finish_game(False)
                else:
                    outcome = ContinueGame(
                        questions_asked=self.questions_asked,
                        questions_remaining=self.questions_remaining,
                        answer=answer.answer,
                    )
            case ValidQuestionSummary(_, _, answer, TurnEndGame(True, _)):
                self._q_count += 1
                outcome = WonGame(
                    questions_asked=self.questions_asked,
                    questions_remaining=self.questions_remaining,
                    answer=answer.answer,
                )
                self.finish_game(True)
            case _:
                raise ValueError(f"Unexpected turn result: {summary!r}")

        return outcome
