import logging
from contextlib import asynccontextmanager
from pathlib import Path

import gradio as gr
from alembic.config import Config
from alembic import command
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from twentyqs.runner import get_view

from .admin import (
    Admin,
    DbFileView,
    HfDatasetView,
    GameSessionAdmin,
    TurnAdmin,
    TurnLogAdmin,
    UserAdmin,
)
from .auth import AdminAuth
from .config import settings
from .repository import Repository

templates = Jinja2Templates(directory=Path(__file__).parent / "templates" / "twentyqs")


logging.basicConfig(level=logging.getLevelName(settings.log_level))


@asynccontextmanager
async def lifespan(app: Starlette):
    if settings.migrate_db:
        # fly.io attaches volumes too late to use `deploy` command to run migrations
        alembic_cfg = Config(settings.alembic_config)
        alembic_cfg.attributes["configure_logger"] = False
        command.upgrade(alembic_cfg, "head")

    db = Repository(db_path=settings.db_path)
    db.init_db(drop=False)

    # the game ui
    blocks = get_view(
        repository=db,
        openai_model=settings.openai_model,
        simple_subject_picker=settings.simple_subject_picker,
        verbose_langchain=settings.verbose_langchain,
        # auth_callback=db.authenticate_player if settings.require_login else None,
    )
    blocks.show_api = False
    gr.mount_gradio_app(app, blocks, path="/play/{username}:{password}")

    # admin site
    admin = Admin(
        app=app,
        engine=db.engine,
        authentication_backend=AdminAuth(
            repository=db,
            secret_key=settings.secret_key,
        ),
        templates_dir=str(Path(__file__).parent / "templates" / "sqladmin"),
    )
    admin.add_view(UserAdmin)
    admin.add_view(GameSessionAdmin)
    admin.add_view(TurnAdmin)
    admin.add_view(TurnLogAdmin)
    admin.add_view(DbFileView)
    admin.add_view(HfDatasetView)

    yield


async def homepage(request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "20 Questions Bot",
        },
    )


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/", homepage),
    ],
)
