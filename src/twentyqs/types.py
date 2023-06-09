from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum, auto
from typing import NamedTuple

from pydantic import BaseModel


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
    question: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TurnValidate:
    is_valid: bool
    reason: str | None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TurnAnswer:
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
    begin: TurnBegin
    validate: TurnValidate
    answer: TurnAnswer
    end_game: TurnEndGame


TurnSummaryT = InvalidQuestionSummary | ValidQuestionSummary


class UserStats(BaseModel):
    class Config:
        frozen = True

    played: int
    unfinished: int
    wins: int
    losses: int
    avg_invalid_questions_per_game: float | None
    avg_questions_to_win: float | None


class ServerStats(BaseModel):
    class Config:
        frozen = True

    users_count: int
    played: int
    unfinished: int
    wins: int
    losses: int
    avg_invalid_questions_per_game: float | None
    avg_questions_to_win: float | None


class UserMeta(BaseModel):
    username: str
    name: str
    stats: UserStats


class TurnReview(BaseModel):
    gamesession_id: int
    valid_q_n: int
    turn_id: int
    subject: str
    question: str
    is_valid: bool
    is_valid_reason: str | None
    answer: str | None
    is_deciding_q: bool | None
