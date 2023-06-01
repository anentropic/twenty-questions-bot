import hashlib
from pathlib import Path
from typing import Type

from datasets import Dataset
from markupsafe import Markup
from pygments import highlight
from pygments.lexers.data import JsonLexer
from pygments.formatters import HtmlFormatter
from sqladmin import (
    Admin as _Admin,
    BaseView as _BaseView,
    ModelView as _ModelView,
    expose,
)
from sqladmin.authentication import login_required
from starlette.requests import Request
from starlette.responses import FileResponse, Response, RedirectResponse

from twentyqs.repository import GameSession, Turn, TurnLog, User
from twentyqs.serde import serialize
from .config import settings
from .repository import Repository


json_lexer = JsonLexer()
html_formatter = HtmlFormatter()
PYGMENTS_CSS = html_formatter.get_style_defs(".highlight")


def json_formatter(val: str):
    return Markup(highlight(val, json_lexer, html_formatter))


def json_detail_formatter(model, attribute):
    val = serialize(getattr(model, attribute.key), indent=2)
    return json_formatter(val)


def obj_formatter(obj):
    return f"{obj.__class__.__name__}(id={obj.id})"


def obj_list_detail_formatter(model, attribute):
    val = getattr(model, attribute.key)
    return [obj_formatter(obj) for obj in val]


class Admin(_Admin):
    db: Repository

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.db = Repository(engine=self.engine)

    def add_model_view(self, view: Type["ModelView"]) -> None:  # type: ignore[override]
        view.db = self.db
        return super().add_model_view(view)

    def add_base_view(self, view: Type["BaseView"]) -> None:  # type: ignore[override]
        view.db = self.db
        return super().add_base_view(view)

    @login_required
    async def index(self, request: Request) -> Response:
        stats = self.db.get_server_stats()
        return self.templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": "20 Questions Bot Admin",
                "pygments_css": PYGMENTS_CSS,
                "server_stats": json_formatter(stats.json(indent=2)),
            },
        )


class BaseView(_BaseView):
    db: Repository


class ModelView(_ModelView):
    db: Repository
    pygments_css = PYGMENTS_CSS
    details_template = "details_with_pygments.html"


class UserAdmin(ModelView, model=User):
    column_list = [
        "id",
        "username",
        "name",
        "is_admin",
    ]
    column_formatters_detail = {
        "games": obj_list_detail_formatter,
    }
    form_excluded_columns = [
        "games",
    ]
    details_template = "user_details.html"

    def user_stats(self, user):
        stats = self.db.get_user_stats(user.username)
        return json_formatter(stats.json(indent=2))


class GameSessionAdmin(ModelView, model=GameSession):
    can_create = False
    can_edit = False
    column_type_formatters = ModelView.column_type_formatters | {
        User: lambda obj: obj.username,
    }
    column_list = [
        "id",
        "user",
        "started_at",
        "finished_at",
        "user_won",
    ]
    column_formatters_detail = {
        "turns": obj_list_detail_formatter,
        "llm_stats": json_detail_formatter,
    }


class TurnAdmin(ModelView, model=Turn):
    can_create = False
    can_edit = False
    column_list = [
        "id",
        "gamesession_id",
        "started_at",
        "questions_remaining",
        "question",
    ]
    column_details_exclude_list = [
        "gamesession_id",
    ]
    column_type_formatters = ModelView.column_type_formatters | {
        GameSession: obj_formatter,
    }
    column_formatters_detail = {
        "logs": obj_list_detail_formatter,
    }


class TurnLogAdmin(ModelView, model=TurnLog):
    can_create = False
    can_edit = False
    column_list = [
        "id",
        "turn_id",
        "timestamp",
        "key",
    ]
    column_details_exclude_list = [
        "turn_id",
    ]
    column_type_formatters = ModelView.column_type_formatters | {
        Turn: obj_formatter,
    }
    column_formatters_detail = {
        "value": json_detail_formatter,
    }


class DbFileView(BaseView):
    name = "Download db file"
    icon = "fa-database"

    @expose("/db/download", methods=["GET"])
    def download(self, request):
        path = Path(settings.db_path)
        return FileResponse(
            path=path,
            media_type="application/octet-stream",
            filename=path.name,
        )


def shortcode(s: str, length: int = 8) -> str:
    return hashlib.shake_128(s.encode("utf-8")).hexdigest(length // 2)


class HfDatasetView(BaseView):
    name = "Push dataset to HF"
    icon = "fa-table"

    @expose("/db/init-push-to-hf", identity="init-push-to-hf", methods=["GET"])
    def confirm(self, request):
        return self.templates.TemplateResponse(
            "push_to_hf.html",
            {
                "request": request,
                "repo_id": settings.hf_repo_id,
            },
        )

    @expose("/db/push-to-hf", identity="do-push-to-hf", methods=["POST"])
    async def push(self, request):
        async with request.form() as form:
            repo_id = form["repo_id"]
        turns = self.db.review_games()
        dataset = Dataset.from_list(
            [turn.dict() for turn in turns],
            split=shortcode(settings.db_path),
        )
        dataset.push_to_hub(
            repo_id=repo_id,
            token=settings.hf_api_token,
        )
        return RedirectResponse(url=request.url_for("admin:index"), status_code=303)
