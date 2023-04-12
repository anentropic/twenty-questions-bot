import re

from langchain import PromptTemplate, LLMChain
from langchain.schema import BaseOutputParser

# TODO:
# in some cases we may need an extra chain to rephrase the user's
# input as a valid question, e.g. it is natural in conversation to
# drop the repetitve "is it" from the question, but this can lead
# to LLM getting picky about the question being a yes/no question

prefix = """A yes/no question is one that could be answered with Yes or No, if we knew the answer.
If we don't know the answer, it can still be a yes/no question.
If the answer is unknowable, it can still be a yes/no question.
If the true answer is uncertain and cannot be definitively stated one way or the other, it can still be a yes/no question.

We are playing the game of 20 Questions. Questions about is it animal/mineral/vegetable are yes/no questions applicable to any subject.
"""

examples = [
    """Subject: frogs
Is this a yes/no question: Does it have legs?
Thought: Frogs have legs therefore the answer is yes
Thought: therefore this is a yes/no question
Reply: Yes
Reason: """,
    """Subject: frogs
Is this a yes/no question: Does it have wings?
Thought: Frogs don't have wings therefore the answer is no
Thought: therefore this is a yes/no question
Reply: Yes
Reason: """,
    """Subject: frogs
Is this a yes/no question: How many legs does it have?
Thought: Frogs have four legs. The answer is a number
Thought: Therefore this is not a yes/no question
Reply: No
Reason: Because it requires a numeric answer.""",
    """Subject: cows
Is this a yes/no question: Are there more of them than sheep?
Thought: I don't know the answer,But if there are more cows then the answer is yes, else no
Thought: Therefore this is a yes/no question.
Reply: Yes
Reason: """,
    """Subject: the Roman Empire
Is this a yes/no question: Does it exist?
Thought: The answer is it did, but it no longer does. Therefore the current answer is no.
Thought: Therefore this is a yes/no question
Reply: Yes
Reason: """,
    """Subject: God
Is this a yes/no question: Does it exist?
Thought: The answer is unknowable. But if we knew the answer it would have to be either yes or no.
Thought: Therefore this is a yes/no question
Reply: Yes
Reason: """,
    """Subject: Bigfoot
Is this a yes/no question: Does it exist?
Thought: The answer is uncertain. But if we knew the answer it would have to be either yes or no
Thought: Therefore this is a yes/no question
Reply: Yes
Reason: """,
]

splitter_re = re.compile(r"(Reply|Reason)\:\s*(?P<value>.*)")


class IsYesNoOutputParser(BaseOutputParser):
    def parse(self, text: str) -> tuple[bool, str]:
        _, answer, reason = text.rsplit("\n", 2)
        answer = splitter_re.match(answer).groupdict()['value'] or None
        reason = splitter_re.match(reason).groupdict()['value'] or None
        is_yes_no = answer.strip().lower() == "yes"
        return is_yes_no, reason


class IsYesNoQuestionChain(LLMChain):
    prompt = PromptTemplate.from_examples(
        examples=examples,
        suffix="""Subject: {subject}
Is this a yes/no question: {question}""",
        prefix=prefix,
        input_variables=["subject", "question"],
        output_parser=IsYesNoOutputParser(),
    )
