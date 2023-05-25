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


TextboxT = dict | str | None
ButtonT = dict | str | None
LabelT = dict | str | None

# history is a list of [user_message, bot_message]
# (can't use tuple as has to be mutable)
HistoryT = list[list[str | None]]
ChatbotT = dict | HistoryT

T = TypeVar("T")
P = ParamSpec("P")

LOADED = "loaded"


class Lockable(Protocol):
    lock: Lock


def with_lock(f: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator (for instance methods) to acquire a lock around the method call.
    """

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        self = cast(Lockable, args[0])
        self.lock.acquire()
        try:
            return f(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            self.lock.release()

    return wrapper


def append_history(
    history: HistoryT,
    user_message: str | None = None,
    bot_message: str | None = None,
):
    """Append a new row (pair of user+bot messages) to the history."""
    history.append([user_message, bot_message])


def set_user_msg(history: HistoryT, user_message: str):
    """Set the user message in the history."""
    logger.debug(f"set_user_msg: {user_message}")
    history[-1][0] = user_message


def set_bot_msg(history: HistoryT, bot_message: str):
    """Set the bot message in the history."""
    logger.debug(f"set_bot_msg: {bot_message}")
    history[-1][1] = bot_message


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


def games_label(val: int) -> str:
    return "game" if val == 1 else "games"


class ViewModel:
    lock: Lock
    controller: GameController

    def __init__(self, controller: GameController, username: str | None = None):
        self.lock = Lock()
        self.controller = controller
        self.username = username
        self.first_run = True

    @with_lock
    def on_load(self, request: gr.Request) -> LabelT:
        """Init a new game."""
        logger.info("ViewModel.on_load")
        if self.username:
            username = self.username
            password = None
        else:
            # this is a hack - gradio JS uses the unsubstituted mount path
            # is its root url, so the request.url is not the real url
            # ...but we can get the real base url from the referer header
            username, password = parse_auth(request.request.headers["referer"])
        self.controller.set_user(username, password)
        return gr.update(value=LOADED, visible=False)

    @with_lock
    def intro(self) -> tuple[TextboxT, ChatbotT]:
        logger.info("ViewModel.intro")
        user_meta = self.controller.get_user_meta()
        history: HistoryT = []
        if self.first_run:
            append_history(
                history,
                bot_message=(
                    f"👋 Hi {user_meta.name},\n"
                    "Let's play a game: I will think of a subject, you have to guess what it is."
                ),
            )
            append_history(
                history,
                bot_message=(
                    "I will do my best to answer correctly, but please bear in mind I "
                    "am only an AI language model...\n\n"
                    "- I don't know about anything that has happened after approx Sept 2021\n"
                    "- I don't always think exactly like a human would\n"
                    "- Your questions and my answers are all recorded, so I can be taught to play better in future"
                ),
            )
        append_history(
            history,
            bot_message=(
                f"You have won **{user_meta.stats.wins}** {games_label(user_meta.stats.wins)} and "
                f"lost **{user_meta.stats.losses}** {games_label(user_meta.stats.losses)} so far, "
                "let's see how you do this time 😉"
            ),
        )
        append_history(
            history, bot_message="🤖💭 Please be patient while I pick a subject..."
        )
        append_history(history)  # empty message to trigger 'loading' animation
        return None, history

    @with_lock
    def start_game(
        self, history: HistoryT, evt: gr.EventData
    ) -> tuple[TextboxT, ChatbotT]:
        logger.info("ViewModel.start_game")
        begun = self.controller.start_game()
        del history[-1]
        set_bot_msg(
            history,
            (
                "💡Ok, I've picked a subject.\n"
                f"Now you have {begun.max_questions} questions to work out what it is!"
            ),
        )
        self.first_run = False
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
                set_bot_msg(history, "Invalid question, please try again.")
                if reason:
                    append_history(history, None, f"({reason})")
            case ContinueGame(_, questions_remaining, Answer(answer)):
                set_bot_msg(history, answer)
                append_history(
                    history, None, f"{questions_remaining} questions remaining"
                )
            case WonGame(questions_asked, _, Answer(answer)):
                set_bot_msg(history, answer)
                append_history(
                    history,
                    None,
                    f"You won!\n\n(You needed {questions_asked} questions to work out the answer)",
                )
                append_history(history, None, "Game over")
                enable_new_game = True
            case LostGame(_, _, Answer(answer), subject):
                set_bot_msg(history, answer)
                append_history(
                    history,
                    None,
                    f"No questions left, I win!\n\nI was thinking of: {subject}",
                )
                append_history(history, None, "Game over")
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
        append_history(history, user_message)
        # disable the input box
        return gr.update(value="", interactive=False), history

    def on_new_game_click(self):
        return gr.update(visible=False)

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
            gr.HTML('<h1 style="font-family: monospace">🤖 Twenty Questions Bot</h1>')

            chatbot = gr.Chatbot()
            question_input = gr.Textbox(
                label="Ask a yes/no question:", interactive=False, visible=False
            )
            new_game = gr.Button("New game", visible=False)

            gr.HTML(
                '<a href="https://github.com/anentropic/twenty-questions-bot">https://github.com/anentropic/twenty-questions-bot</a>'
            )

            # we can't chain .then from the load event, and State obj doesn't have
            # change events, so we use a hidden Textbox as a state substitute
            loaded_sentinel = gr.Textbox("", visible=False)
            loaded_sentinel.change(self.intro, None, [question_input, chatbot]).success(
                self.start_game, [chatbot], [question_input, chatbot]
            )

            view.load(self.on_load, None, [loaded_sentinel])

            question_input.submit(
                self.on_question_input,
                [question_input, chatbot],
                [question_input, chatbot],
                queue=False,
            ).success(
                self.after_question_input,
                [chatbot],
                [question_input, chatbot, new_game],
            )
            new_game.click(self.on_new_game_click, None, [new_game]).success(
                self.intro, None, [question_input, chatbot]
            ).success(self.start_game, [chatbot], [question_input, chatbot])

        view.auth = auth_callback
        view.auth_message = None
        return view
