
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import TypedDict

from langchain.schema import BaseLanguageModel

from twentyqs.chains.answer_question import AnswerQuestionChain, Answer
from twentyqs.chains.deciding_question import IsDecidingQuestionChain
from twentyqs.chains.is_yes_no_question import IsYesNoQuestionChain
from twentyqs.chains.pick_subject import (
    PickSubjectChain,
    OBJECT_CATEGORIES,
    PEOPLE_CATEGORIES,
    PLACE_CATEGORIES,
    SIMPLE_CATEGORY,
)


logger = logging.getLogger(__name__)


class TurnLog(TypedDict, total=False):
    question: str
    q_count: int
    is_yes_no_question: tuple[bool, str]
    answer_question: tuple[Answer | str | None, str]
    is_deciding_question: bool


class Game:
    """A game of 20 Questions."""

    llm: BaseLanguageModel

    max_questions: int = 20
    q_count: int = 0
    _subject: str
    history: list[str]

    num_candidates: int = 10
    simple_subject_picker: bool

    pick_subject_chain: PickSubjectChain
    is_yes_no_question_chain: IsYesNoQuestionChain
    answer_question_chain: AnswerQuestionChain
    deciding_question_chain: IsDecidingQuestionChain

    turn_logs: list[TurnLog] = []

    def __init__(
        self,
        llm: BaseLanguageModel,
        simple_subject_picker: bool = False,
        history: list[str] | None = None,
    ):
        self.llm = llm
        self.history = history or []
        self.simple_subject_picker = simple_subject_picker

        self.pick_subject_chain = PickSubjectChain(llm=llm, verbose=True)
        self.is_yes_no_question_chain = IsYesNoQuestionChain(llm=llm, verbose=True)
        self.answer_question_chain = AnswerQuestionChain(llm=llm, verbose=True)
        self.deciding_question_chain = IsDecidingQuestionChain(llm=llm, verbose=True)

    @property
    def subject(self) -> str:
        if self._subject is None:
            self.set_subject()
        return self._subject
    
    def set_subject(self) -> None:
        self._subject = self.pick_subject()
        self.history.append(self._subject)

    def pick_subject(self) -> str:
        """Pick a subject for the game."""
        if self.simple_subject_picker:
            candidates = self.pick_subject_chain.predict_and_parse(
                num=self.num_candidates,
                category=SIMPLE_CATEGORY,
                seen=self.history,
            )
        else:
            category = random.choice((
                OBJECT_CATEGORIES,
                PEOPLE_CATEGORIES,
                PLACE_CATEGORIES,
            ))
            candidates = []
            for theme in category:
                candidates.extend(
                    self.pick_subject_chain.predict_and_parse(
                        num=self.num_candidates,
                        category=theme,
                        seen=self.history,
                    )
                )
        return random.choice(candidates)

    def turn(self) -> TurnLog:
        """Play a turn of the game."""
        turn_log: TurnLog = {}
        turn_log['q_count'] = self.q_count

        question = self.ask_question()
        turn_log['question'] = question

        valid, reason = self.is_yes_no_question_chain.predict_and_parse(
            subject=self.subject,
            question=question,
        )
        turn_log['is_yes_no_question'] = valid, reason
        if not valid:
            return turn_log
        
        answer, justification = self.answer_question_chain.predict_and_parse(
            today=datetime.now().strftime("%d %B %Y"),
            subject=self.subject,
            question=question,
        )
        turn_log['answer_question'] = answer, justification

        if answer is Answer.YES:
            is_deciding_question = self.deciding_question_chain.predict_and_parse(
                subject=self.subject,
                question=question,
            )
            turn_log['is_deciding_question'] = is_deciding_question
        else:
            turn_log['is_deciding_question'] = False

        self.q_count += 1
        return turn_log

    def ask_question(self) -> str:
        """Ask a question about the subject."""
        while True:
            question = input("Ask a yes/no question: ")
            question = question.strip()
            if question:
                if not question.endswith("?"):
                    question += "?"
                return question

    def play(self):
        """Play a game of 20 Questions."""
        self.set_subject()
        print("Ok, I've picked a subject. Now you have to work out what it is!")
        print(
            "(I will do my best to answer honestly, but please bear in mind I "
            "am only a 'Large Language Model' and I don't know about anything "
            "that has happened after September 2021)"
        )
        while self.q_count < 20:
            turn_log = self.turn()
            self.turn_logs.append(turn_log)
            logger.info(turn_log)
            match turn_log:
                case {'is_yes_no_question': (False, reason)}:
                    print("Invalid question, please try again")
                    print(f"({reason})")
                    continue
                case {'answer_question': (answer, _)}:
                    print(answer.value)
                    if turn_log['is_deciding_question']:
                        print("You won!")
                        print(f"(you needed {self.q_count} questions to work out the answer)")
                        break
                    print(f"{self.max_questions - self.q_count} questions remaining")
        else:
            print("No questions left, I win!")
            print(f"I was thinking of: {self.subject}")
        print("Game over")
