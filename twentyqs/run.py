import argparse
import logging
from contextlib import contextmanager
from dataclasses import dataclass

from langchain import OpenAI
from langchain.callbacks import get_openai_callback
from langchain.callbacks.openai_info import OpenAICallbackHandler

from twentyqs.brain import AnswerBot
from twentyqs.controller import GameController
from twentyqs.repository import create_tables
from twentyqs.view import ViewModel


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenAIStatsContext:
    _callback: OpenAICallbackHandler

    def get_stats(self):
        return {
            "total_tokens": self._callback.total_tokens,
            "prompt_tokens": self._callback.prompt_tokens,
            "completion_tokens": self._callback.completion_tokens,
            "successful_requests": self._callback.successful_requests,
            "total_cost": self._callback.total_cost,
        }


@contextmanager
def openai_stats_context():
    with get_openai_callback() as callback:
        yield OpenAIStatsContext(callback)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", type=str)
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo")
    parser.add_argument("--simple-subject-picker", action="store_true")
    parser.add_argument("--verbose-langchain", action="store_true")
    parser.add_argument("--db-path", type=str, default="twentyqs.db")
    parser.add_argument("--clear-db", action="store_true")
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    create_tables(db_name=args.db_path, drop=args.clear_db)

    llm = OpenAI(temperature=0, model_name=args.model)
    answerer = AnswerBot(
        llm=llm,
        simple_subject_picker=args.simple_subject_picker,
        langchain_verbose=args.verbose_langchain,
    )
    controller = GameController(
        username=args.username,
        answerer=answerer,
        stats_context_mgr=openai_stats_context(),
    )
    view_model = ViewModel(controller)
    view = view_model.create_view()
    view.launch()
