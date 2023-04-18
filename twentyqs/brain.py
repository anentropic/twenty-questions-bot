
import logging
import random
import warnings
from datetime import datetime
from typing import cast

from langchain import OpenAI
from langchain.schema import BaseLanguageModel

from twentyqs.chains.answer_question import AnswerQuestionChain, Answer, ParsedT as AnswerParsedT
from twentyqs.chains.deciding_question import IsDecidingQuestionChain, ParsedT as DecidingParsedT
from twentyqs.chains.is_yes_no_question import IsYesNoQuestionChain, ParsedT as IsYesNoParsedT
from twentyqs.chains.pick_subject import (
    PickSubjectChain,
    ParsedT as PickSubjectParsedT,
    OBJECT_CATEGORIES,
    PEOPLE_CATEGORIES,
    PLACE_CATEGORIES,
    SIMPLE_CATEGORY,
)
from twentyqs.types import (
    TurnResult,
    TurnBegin,
    TurnSummaryT,
    TurnValidate,
    TurnAnswer,
    TurnEndGame,
    InvalidQuestionSummary,
    ValidQuestionSummary,
)


logger = logging.getLogger(__name__)


class AnswerBot:
    """
    A game of 20 Questions.
    """

    llm: BaseLanguageModel

    max_questions: int = 20
    _q_count: int = 0
    _subject: str
    history: list[str]

    num_candidates: int = 10
    simple_subject_picker: bool

    pick_subject_chain: PickSubjectChain
    is_yes_no_question_chain: IsYesNoQuestionChain
    answer_question_chain: AnswerQuestionChain
    deciding_question_chain: IsDecidingQuestionChain

    def __init__(
        self,
        llm: BaseLanguageModel,
        simple_subject_picker: bool = False,
        history: list[str] | None = None,
        langchain_verbose: bool = False,
    ):
        self.llm = llm

        self.history = history or []
        self.simple_subject_picker = simple_subject_picker

        self.pick_subject_chain = PickSubjectChain(llm=llm, verbose=langchain_verbose)
        self.is_yes_no_question_chain = IsYesNoQuestionChain(llm=llm, verbose=langchain_verbose)
        self.answer_question_chain = AnswerQuestionChain(llm=llm, verbose=langchain_verbose)
        self.deciding_question_chain = IsDecidingQuestionChain(llm=llm, verbose=langchain_verbose)

    @classmethod
    def using_openai(
        cls,
        openai_model_name: str = "gpt-3.5-turbo",
        simple_subject_picker: bool = False,
        history: list[str] | None = None,
        *args,
        **kwargs
    ) -> "AnswerBot":
        llm = OpenAI(temperature=0, model_name=openai_model_name, *args, **kwargs)
        return cls(llm=llm, simple_subject_picker=simple_subject_picker, history=history)

    @property
    def questions_asked(self) -> int:
        """
        Valid questions asked so far.
        """
        return self._q_count

    @property
    def questions_remaining(self) -> int:
        return self.max_questions - self._q_count

    @property
    def subject(self) -> str:
        if self._subject is None:
            self.set_subject()
        return self._subject
    
    def set_subject(self) -> None:
        self._subject = self.pick_subject()
        self.history.append(self._subject)
        self._q_count = 0

    def pick_subject(self) -> str:
        """
        Pick a subject for the game.
        """
        if self.simple_subject_picker:
            candidates = cast(
                PickSubjectParsedT,
                self.pick_subject_chain.predict_and_parse(
                    num=self.num_candidates,
                    category=SIMPLE_CATEGORY,
                    seen=self.history,
                )
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
                    cast(
                        PickSubjectParsedT,
                        self.pick_subject_chain.predict_and_parse(
                            num=self.num_candidates,
                            category=theme,
                            seen=self.history,
                        )
                    )
                )
        return random.choice(candidates)

    def process_turn(self, question: str) -> TurnSummaryT:
        """
        Play a turn of the game.
        """
        turn_begin = TurnBegin(
            questions_asked=self.questions_asked,
            questions_remaining=self.questions_remaining,
            question=question,
        )

        is_valid, reason = cast(
            IsYesNoParsedT,
            self.is_yes_no_question_chain.predict_and_parse(
                subject=self.subject,
                question=question,
            )
        )
        turn_validate = TurnValidate(
            is_valid=is_valid,
            reason=reason,
        )
        if not is_valid:
            return InvalidQuestionSummary(
                begin=turn_begin,
                validate=turn_validate,
            )

        self._q_count += 1

        answer, justification = cast(
            AnswerParsedT,
            self.answer_question_chain.predict_and_parse(
                today=datetime.now().strftime("%d %B %Y"),
                subject=self.subject,
                question=question,
            )
        )
        # TODO: log these failures
        # should parser behave differently?
        if answer is None:
            raise ValueError("Failed to parse answer from LLM response.")
        if not isinstance(answer, Answer):
            warnings.warn(f"Unexpected answer: {answer}")
            
        turn_answer = TurnAnswer(
            questions_asked=self.questions_asked,
            questions_remaining=self.questions_remaining,
            answer=answer,
            justification=justification,
        )

        if answer is Answer.YES:
            is_deciding_question = cast(
                DecidingParsedT,
                self.deciding_question_chain.predict_and_parse(
                    subject=self.subject,
                    question=question,
                )
            )
        else:
            is_deciding_question = False

        turn_end_game = TurnEndGame(
            is_deciding_q=is_deciding_question,
        )

        # TODO: maybe this should just return ANSWERED and the
        # q_count logic can move to the controller
        if is_deciding_question:
            result = TurnResult.WIN
        elif self._q_count == self.max_questions:
            result = TurnResult.LOSE
        else:
            result = TurnResult.CONTINUE

        return ValidQuestionSummary(
            result=result,
            begin=turn_begin,
            validate=turn_validate,
            answer=turn_answer,
            end_game=turn_end_game,
        )
