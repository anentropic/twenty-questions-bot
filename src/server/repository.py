from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, select

from twentyqs.repository import (
    with_session,
    Repository as BaseRepository,
    User,
)
from .config import get_settings


class Repository(BaseRepository):

    def init_db(self, drop=False):
        super().init_db(drop=drop)
        with Session(self.engine) as session:
            session.exec(
                insert(User).values({
                    "username": "admin",
                    "password": get_settings().admin_password,
                    "is_admin": True,
                }).on_conflict_do_nothing(index_elements=['username'])
            )
            session.commit()

    @with_session
    def get_by_username(self, session: Session, username: str) -> User | None:
        return session.exec(
            select(User).where(User.username == username)
        ).one_or_none()

    @with_session
    def get_admin_by_username(self, session: Session, username: str) -> User | None:
        return session.exec(
            select(User).where(
                User.username == username,
                User.is_admin == True,
            )
        ).one_or_none()

    def authenticate_admin(self, username: str, password: str) -> bool:
        admin = self.get_by_username(username)
        if not admin:
            return False
        if not admin.password == password:
            return False
        return True
