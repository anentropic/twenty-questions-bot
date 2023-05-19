import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Protocol

from twentyqs.brain import AnswerBot
from twentyqs.repository import Repository, User, GameSession, Turn
from twentyqs.types import (
    LogKey,
    JsonT,
    TurnResult,
    TurnSummaryT,
    InvalidQuestionSummary,
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


class GameController:
    answerer: AnswerBot
    stats_context_factory: StatsContextManagerFactory | None
    _stats_context_mgr: StatsContextManager | None = None
    game_stats_context: StatsContext | None = None
    user: User
    session: GameSession | None = None

    def __init__(
        self,
        repository: Repository,
        answerer: AnswerBot,
        stats_context_factory: StatsContextManagerFactory | None = None,
    ):
        self.db = repository
        self.answerer = answerer
        self.stats_context_factory = stats_context_factory

    def start_game(self, username: str) -> GameBegun:
        """
        Start a new game.
        """
        user = self.db.get_or_create_user(username)

        subject_history = self.db.user_subject_history(user.username)
        self.answerer.history = subject_history

        if self.stats_context_factory:
            self._stats_context_mgr = mgr = self.stats_context_factory()
            self.game_stats_context = mgr.__enter__()

        self.answerer.set_subject()
        self.session = self.db.start_game(user=user, subject=self.answerer.subject)
        return GameBegun(
            max_questions=self.answerer.max_questions,
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
        turn = self.db.start_turn(game=self.session, question=question)

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
            case ValidQuestionSummary(TurnResult.CONTINUE, begin, _, answer, _):
                outcome = ContinueGame(
                    questions_asked=answer.questions_asked,
                    questions_remaining=answer.questions_remaining,
                    answer=answer.answer,
                )
            case ValidQuestionSummary(TurnResult.WIN, begin, _, answer, _):
                outcome = WonGame(
                    questions_asked=answer.questions_asked,
                    questions_remaining=answer.questions_remaining,
                    answer=answer.answer,
                )
                self.finish_game(True)
            case ValidQuestionSummary(TurnResult.LOSE, begin, _, answer, _):
                outcome = LostGame(
                    questions_asked=answer.questions_asked,
                    questions_remaining=answer.questions_remaining,
                    answer=answer.answer,
                    subject=self.session.subject,
                )
                self.finish_game(False)
            case _:
                raise ValueError(f"Unexpected turn result: {summary!r}")

        return outcome
