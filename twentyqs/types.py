from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum, auto
from typing import NamedTuple


JsonT = dict[str, "JsonT"] | list["JsonT"] | str | float | bool | None


class Answer(StrEnum):
    YES = "Yes"
    NO = "No"
    SOMETIMES = "Sometimes"
    DONT_KNOW = "I don't know"


class LogKey(StrEnum):
    BEGIN_TURN = "BEGIN_TURN"
    VALIDATE_QUESTION = "VALIDATE_QUESTION"
    ANSWER_QUESTION = "ANSWER_QUESTION"
    IS_DECIDING_QUESTION = "IS_DECIDING_QUESTION"


class TurnResult(Enum):
    CONTINUE = auto()
    WIN = auto()
    LOSE = auto()


@dataclass(frozen=True)
class TurnBegin:
    questions_asked: int  # (valid questions only)
    questions_remaining: int
    question: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TurnValidate:
    is_valid: bool
    reason: str | None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TurnAnswer:
    questions_asked: int  # (valid questions only)
    questions_remaining: int
    answer: str
    justification: str | None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TurnEndGame:
    is_deciding_q: bool
    timestamp: datetime = field(default_factory=datetime.now)


class InvalidQuestionSummary(NamedTuple):
    begin: TurnBegin
    validate: TurnValidate


class ValidQuestionSummary(NamedTuple):
    result: TurnResult
    begin: TurnBegin
    validate: TurnValidate
    answer: TurnAnswer
    end_game: TurnEndGame


TurnSummaryT = InvalidQuestionSummary | ValidQuestionSummary


@dataclass(frozen=True)
class UserStats:
    played: int
    wins: int
    losses: int
    overall_avg_questions: float
    avg_questions_to_win: float
