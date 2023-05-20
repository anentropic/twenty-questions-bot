import logging
from collections.abc import Callable
from functools import wraps
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
ButtonT = dict | str

# history is a list of [user_message, bot_message]
# (can't use tuple as has to be mutable)
HistoryT = list[list[str | None]]
ChatbotT = dict | HistoryT

T = TypeVar("T")
P = ParamSpec("P")


class Lockable(Protocol):
    lock: Lock


def with_lock(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator (for instance methods) to acquire a lock around the method call.
    """

    @wraps(func)
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


def parse_auth(urlpath: str) -> tuple[str, str]:
    segment = urlpath.rstrip("/").rsplit("/", 1)[-1]
    username, password = segment.split(":")
    return username, password


class ViewModel:
    lock: Lock
    controller: GameController

    def __init__(self, controller: GameController, username: str | None = None):
        self.lock = Lock()
        self.controller = controller
        self.username = username

    @with_lock
    def on_load(self, request: gr.Request) -> tuple[TextboxT, ChatbotT]:
        """Init a new game."""
        if self.username:
            username = self.username
        else:
            # this is a hack - gradio JS uses the unsubstituted mount path
            # is its root url, so the request.url is not the real url
            # ...but we can get the real base url from the referer header
            username, password = parse_auth(request.request.headers["referer"])
            valid = self.controller.db.authenticate_player(username, password)
            if not valid:
                raise ValueError("Invalid username/passcode")

        begun = self.controller.start_game(username)
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
        return gr.update(interactive=True, visible=True), history

    @with_lock
    def after_question_input(
        self, history: HistoryT
    ) -> tuple[TextboxT, ChatbotT, ButtonT]:
        """Process a game turn."""
        question = get_user_msg(history)
        assert question is not None
        outcome = self.controller.take_turn(question)
        logger.debug(f"ViewModel.after_input outcome: {outcome}")
        enable_new_game = False
        match outcome:
            case InvalidQuestion(_, reason):
                history = set_bot_msg(history, "Invalid question, please try again.")
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
                    history,
                    None,
                    f"You won!\n\n(You needed {questions_asked} questions to work out the answer)",
                )
                history = append_history(history, None, "Game over")
                enable_new_game = True
            case LostGame(_, _, Answer(answer), subject):
                history = set_bot_msg(history, answer)
                history = append_history(
                    history,
                    None,
                    f"No questions left, I win!\n\nI was thinking of: {subject}",
                )
                history = append_history(history, None, "Game over")
                enable_new_game = True

        # re-enable the input box
        return (
            gr.update(interactive=not enable_new_game, visible=not enable_new_game),
            history,
            gr.update(visible=enable_new_game),
        )

    def on_question_input(
        self, user_message: str, history: HistoryT
    ) -> tuple[TextboxT, ChatbotT]:
        user_message = user_message.strip()
        # TODO: gradio error handling is meh
        # if not user_message:
        #     raise gr.Error("Please enter a question")
        history = append_history(history, user_message)
        # disable the input box
        return gr.update(value="", interactive=False), history

    def on_new_game_click(self):
        question_input, chatbot = self.on_load()
        return question_input, chatbot, gr.update(visible=False)

    def create_view(
        self, auth_callback: Callable[[str, str], bool] | None
    ) -> gr.Blocks:
        """
        Returns the gradio blocks UI object.

        If `auth_callback` is given, will force Gradio to display login form.
        """
        if auth_callback and self.username:
            raise ValueError("Cannot provide both `auth_callback` and `username`")

        with gr.Blocks() as view:
            chatbot = gr.Chatbot(
                [
                    [
                        None,
                        "🤖💭 Please be patient while I pick a subject...",
                    ],
                ]
            )
            question_input = gr.Textbox(
                label="Ask a yes/no question:", interactive=False
            )
            new_game = gr.Button("New game", visible=False)

            view.load(self.on_load, [], [question_input, chatbot])

            question_input.submit(
                self.on_question_input,
                [question_input, chatbot],
                [question_input, chatbot],
                queue=False,
            ).success(
                self.after_question_input,
                chatbot,
                [question_input, chatbot, new_game],
            )
            new_game.click(
                self.on_new_game_click, None, [question_input, chatbot, new_game]
            )

        view.auth = auth_callback
        view.auth_message = None
        return view
