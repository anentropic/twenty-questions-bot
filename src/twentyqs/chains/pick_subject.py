import logging
import re

from langchain import PromptTemplate, LLMChain
from langchain.schema import BaseOutputParser

logger = logging.getLogger(__name__)


# TODO:
# - one time having "Taj Mahal" as the lone item in the 'already used' list
#   caused it to pick "The Taj Mahal (already used)" as the subject (the actual
#   game played fine and it accepted 'Taj Mahal' as the answer though)
# - more problematic, the 'already used' list tends to get used as examples so
#   e.g. with SIMPLE_CATEGORY once it has picked one 'place' it will tend to pick
#   more 'places' after that
# - ...to be seen whether the themed category prompts totally overcome that
template = """You are an AI about to play a game of "20 Questions" with a human.

Before we start the game we need to prepare a lists of possible subjects. The human will be asking questions trying to guess the identity of the subject. So the subjects should all be well-known to most people.

The following subjects have already been used and should not appear in the lists:
{seen}

Begin! Remember, each item in the list should be unique with no repeats.

{num} {category}:
"""

# does pretty well:
SIMPLE_CATEGORY = "subjects for the game '20 Questions'"

# themed prompts can provide more variety:
PEOPLE_CATEGORIES = [
    "historical people",
    "celebrities",
    "leaders",
    "interesting people (not celebrities or leaders)",
    "well-known sports people",
    "musicians",
]
OBJECT_CATEGORIES = [
    "things (not places, people or groups of people)",  # generic
    "interesting objects (not places, people or groups of people)",  # good, not wild
    "interesting things (not places, people or groups of people)",  # tends to give some landmarks (i.e. places) too
]
PLACE_CATEGORIES = [
    "common places",
    "interesting places",
    "historic places",
]

splitter_re = re.compile(r"^\d+\.\s*(.+)$", re.MULTILINE)


ParsedT = list[str]

class NumberedListParser(BaseOutputParser[ParsedT]):
    def parse(self, text: str) -> ParsedT:
        logger.debug("NumberedListParser.parse: %s", text)
        return splitter_re.findall(text)


class PickSubjectChain(LLMChain):
    """
    NOTE:
    The LLM will tend to pick much the same items each time. So we need to keep
    a history of items that have already been used and ask it to exclude them.
    (this history should persist across multiple game sesisons)
    """
    prompt = PromptTemplate(
        template=template,
        input_variables=["num", "category", "seen"],
        output_parser=NumberedListParser(),
    )
