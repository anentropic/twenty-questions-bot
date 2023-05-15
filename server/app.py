import logging
from contextlib import asynccontextmanager

import gradio as gr  # type: ignore
from sqladmin import Admin, ModelView
from starlette.applications import Starlette

from twentyqs.repository import create_tables
from twentyqs.runner import get_view

from .auth import AdminAuth, game_auth
from .config import get_settings
from .repository import User, init_db, get_engine


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.is_admin]  # type: ignore


@asynccontextmanager
async def lifespan(app: Starlette):
    settings = get_settings()

    logging.basicConfig(level=logging.getLevelName(settings.log_level))

    init_db()  # SQLmodel (creates admin user)

    create_tables(db_name=settings.db_path, drop=False)  # Peewee

    admin = Admin(app=app, engine=get_engine(), authentication_backend=AdminAuth())
    admin.add_view(UserAdmin)

    blocks = get_view(
        openai_model=settings.openai_model,
        simple_subject_picker=settings.simple_subject_picker,
        verbose_langchain=settings.verbose_langchain,
        auth_callback=game_auth,
    )

    gr.mount_gradio_app(app, blocks, path="/")

    yield


app = Starlette(
    lifespan=lifespan,
)
