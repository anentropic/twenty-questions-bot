#!/usr/bin/env python3
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable

import gradio as gr  # type: ignore
from langchain import OpenAI
from langchain.callbacks import get_openai_callback
from langchain.callbacks.openai_info import OpenAICallbackHandler

from twentyqs.brain import AnswerBot
from twentyqs.controller import GameController
from twentyqs.repository import create_tables
from twentyqs.ui import ViewModel


"""
IMPORTANT:
Beware of https://gradio.app/sharing-your-app/#security-and-file-access
> Gradio apps grant users access to three kinds of files:
> - Files in the same folder (or a subdirectory) of where the Gradio script is launched from. 
"""

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


def get_view(
    openai_model: str,
    simple_subject_picker: bool,
    verbose_langchain: bool,
    auth_callback: Callable[[str, str], bool] | None = None,
) -> gr.Blocks:
    llm = OpenAI(temperature=0, model_name=openai_model)
    answerer = AnswerBot(
        llm=llm,
        simple_subject_picker=simple_subject_picker,
        langchain_verbose=verbose_langchain,
    )
    controller = GameController(
        answerer=answerer,
        stats_context_factory=openai_stats_context,
    )
    view_model = ViewModel(controller)
    return view_model.create_view(auth_callback=auth_callback)


def run(
    openai_model: str,
    db_path: str,
    clear_db: bool,
    simple_subject_picker: bool,
    verbose_langchain: bool,
    log_level: str,
):
    logging.basicConfig(level=logging.getLevelName(log_level))

    create_tables(db_name=db_path, drop=clear_db)

    view = get_view(
        openai_model=openai_model,
        simple_subject_picker=simple_subject_picker,
        verbose_langchain=verbose_langchain,
    )
    view.launch(show_api=False)
