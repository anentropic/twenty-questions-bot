from pathlib import Path
from typing import List

from markupsafe import Markup
from pygments import highlight
from pygments.lexers.data import JsonLexer
from pygments.formatters import HtmlFormatter
from sqladmin import BaseView, ModelView, expose
from starlette.responses import FileResponse

from twentyqs.repository import GameSession, Turn, TurnLog, User
from twentyqs.serde import serialize
from server.config import get_settings


json_lexer = JsonLexer()
html_formatter = HtmlFormatter()


def json_detail_formatter(model, attribute):
    val = serialize(getattr(model, attribute.key), indent=2)
    return Markup(highlight(val, json_lexer, html_formatter))


def obj_formatter(obj):
    return f"{obj.__class__.__name__}(id={obj.id})"


def obj_list_detail_formatter(model, attribute):
    val = getattr(model, attribute.key)
    return [obj_formatter(obj) for obj in val]


class UserAdmin(ModelView, model=User):
    column_list = [
        "id",
        "username",
        "is_admin",
    ]
    column_formatters_detail = {
        "games": obj_list_detail_formatter,
    }


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
    pygments_css = html_formatter.get_style_defs(".highlight")
    details_template = "details_with_pygments.html"


class TurnAdmin(ModelView, model=Turn):
    can_create = False
    can_edit = False
    column_list = [
        "id",
        "gamesession_id",
        "started_at",
        "finished_at",
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
    pygments_css = html_formatter.get_style_defs(".highlight")
    details_template = "details_with_pygments.html"


class DbFileView(BaseView):
    name = "Download db file"
    icon = "fa-database"

    @expose("/db/download", methods=["GET"])
    def download(self, request):
        settings = get_settings()
        path = Path(settings.db_path)
        return FileResponse(
            path=path,
            media_type="application/octet-stream",
            filename=path.name,
        )
