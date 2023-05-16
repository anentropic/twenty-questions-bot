from contextlib import contextmanager
from functools import lru_cache
from typing import Optional

from sqlalchemy.future import Engine
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Field, Session, SQLModel, create_engine, select

from twentyqs.repository import get_code
from .config import get_settings


@lru_cache()
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        f"sqlite:///{settings.db_path}",
        echo=True,
        connect_args={"check_same_thread": False},
    )


def init_db():
    settings = get_settings()
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.exec(
            insert(User).values({
                "username": "admin",
                "password": settings.admin_password,
                "is_admin": True,
            }).on_conflict_do_nothing(index_elements=['username'])
        )
        session.commit()


@contextmanager
def get_session():
    engine = get_engine()
    with Session(engine) as session:
        yield session


class User(SQLModel, table=True):
    """
    TODO: rewrite twentyqs to use SQLmodel instead of Peewee so we
    don't have to duplicate this definition across two ORMs.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password: str = Field(
        max_length=16,
        default_factory=get_code,
    )
    is_admin: bool = False


def get_by_username(username: str) -> User | None:
    with get_session() as session:
        return session.exec(
            select(User).where(User.username == username)
        ).one_or_none()



def get_admin_by_username(username: str) -> User | None:
    with get_session() as session:
        return session.exec(
            select(User).where(
                User.username == username,
                User.is_admin == True,
            )
        ).one_or_none()
