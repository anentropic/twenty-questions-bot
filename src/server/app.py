import logging
from contextlib import asynccontextmanager
from pathlib import Path

import gradio as gr  # type: ignore
from sqladmin import Admin
from starlette.applications import Starlette

from twentyqs.runner import get_view

from .admin import (
    DbFileView,
    GameSessionAdmin,
    TurnAdmin,
    TurnLogAdmin,
    UserAdmin,
)
from .auth import AdminAuth
from .config import get_settings
from .repository import Repository


@asynccontextmanager
async def lifespan(app: Starlette):
    settings = get_settings()

    logging.basicConfig(level=logging.getLevelName(settings.log_level))

    db = Repository(settings.db_path)
    db.init_db(drop=False)

    admin = Admin(
        app=app,
        engine=db.engine,
        authentication_backend=AdminAuth(
            repository=db,
            secret_key=settings.secret_key,
        ),
        templates_dir=str(Path(__file__).parent / "templates"),
    )
    admin.add_view(UserAdmin)
    admin.add_view(GameSessionAdmin)
    admin.add_view(TurnAdmin)
    admin.add_view(TurnLogAdmin)
    admin.add_view(DbFileView)

    blocks = get_view(
        repository=db,
        openai_model=settings.openai_model,
        simple_subject_picker=settings.simple_subject_picker,
        verbose_langchain=settings.verbose_langchain,
        auth_callback=db.authenticate_admin,
    )

    gr.mount_gradio_app(app, blocks, path="/")

    yield


app = Starlette(
    lifespan=lifespan,
)
