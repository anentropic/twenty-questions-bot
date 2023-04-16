import logging
from collections.abc import Callable
from threading import Lock
from typing import ParamSpec, Protocol, TypeVar, cast

import gradio as gr  # type: ignore

from twentyqs.controller import (
    GameController,
    InvalidQuestion,
    ContinueGame,
    WonGame,
    LostGame,
)
from twentyqs.types import Answer

logger = logging.getLogger(__name__)


TextboxT = dict | str

# history is a list of [user_message, bot_message]
# (can't use tuple as has to be mutable)
HistoryT = list[list[str | None]]
ChatbotT = dict | HistoryT

T = TypeVar('T')
P = ParamSpec("P")


class Lockable(Protocol):
    lock: Lock


def with_lock(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator (for instance methods) to acquire a lock around the method call.
    """
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        self = cast(Lockable, args[0])
        self.lock.acquire()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            self.lock.release()
    return wrapper


def append_history(
    history: HistoryT,
    user_message: str | None = None,
    bot_message: str | None = None,
) -> HistoryT:
    """Append a new row (pair of user+bot messages) to the history."""
    return history + [[user_message, bot_message]]


def set_user_msg(history: HistoryT, user_message: str) -> HistoryT:
    """Set the user message in the history."""
    logger.debug(f"set_user_msg: {user_message}")
    history[-1][0] = user_message
    return history


def set_bot_msg(history: HistoryT, bot_message: str) -> HistoryT:
    """Set the bot message in the history."""
    logger.debug(f"set_bot_msg: {bot_message}")
    history[-1][1] = bot_message
    return history


def get_user_msg(history: HistoryT) -> str | None:
    """Get the user message from the history."""
    return history[-1][0]


def get_bot_msg(history: HistoryT) -> str | None:
    """Get the bot message from the history."""
    return history[-1][1]


class ViewModel:

    lock: Lock
    controller: GameController

    def __init__(self, controller: GameController):
        self.lock = Lock()
        self.controller = controller

    @with_lock
    def on_load(self) -> tuple[TextboxT, ChatbotT]:
        """Process a game turn."""
        begun = self.controller.start_game()
        history = [
            [
                None,
                "Ok, I've picked a subject.\n"
                f"Now you have {begun.max_questions} questions to work out what it is!",
            ],
            [
                None,
                "(I will do my best to answer honestly, but please bear in mind I "
                "am only a 'Large Language Model' and I don't know about anything "
                "that has happened after September 2021...)",
            ],
        ]
        return gr.update(interactive=True), history

    @with_lock
    def after_input(self, history: HistoryT) -> tuple[TextboxT, ChatbotT]:
        """Process a game turn."""
        question = get_user_msg(history)
        assert question is not None
        outcome = self.controller.take_turn(question)
        logger.debug(f"ViewModel.after_input outcome: {outcome}")
        match outcome:
            case InvalidQuestion(_, reason):
                history = set_bot_msg(history, f"Invalid question, please try again.")
                if reason:
                    history = append_history(history, None, f"({reason})")
            case ContinueGame(_, questions_remaining, Answer(answer)):
                history = set_bot_msg(history, answer)
                history = append_history(
                    history, None, f"{questions_remaining} questions remaining"
                )
            case WonGame(questions_asked, _, Answer(answer)):
                history = set_bot_msg(history, answer)
                history = append_history(
                    history, None, f"You won!\n\n(You needed {questions_asked} questions to work out the answer)"
                )
                history = append_history(history, None, "Game over")
            case LostGame(_, _, Answer(answer), subject):
                history = set_bot_msg(history, answer)
                history = append_history(
                    history, None, f"No questions left, I win!\n\n(I was thinking of: {subject})"
                )
                history = append_history(history, None, "Game over")

        # re-enable the input box
        return gr.update(interactive=True), history

    def on_input(self, user_message: str, history: HistoryT) -> tuple[TextboxT, ChatbotT]:
        user_message = user_message.strip()
        if not user_message:
            return "", history
        history = append_history(history, user_message)
        # disable the input box
        return gr.update(value="", interactive=False), history

    def create_view(self) -> gr.Blocks:
        """
        Returns the gradio blocks UI object.
        """
        with gr.Blocks() as view:
            chatbot = gr.Chatbot()
            msg = gr.Textbox(label="Ask a yes/no question:", interactive=False)

            view.load(self.on_load, None, [msg, chatbot])

            msg.submit(self.on_input, [msg, chatbot], [msg, chatbot], queue=False).then(
                self.after_input, chatbot, [msg, chatbot]
            )
        return view
