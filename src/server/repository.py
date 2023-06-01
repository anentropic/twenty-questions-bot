import logging

from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session

from twentyqs.repository import Repository as BaseRepository, User
from .config import settings

logger = logging.getLogger(__name__)


class Repository(BaseRepository):
    def init_db(self, drop=False):
        # TODO: this could be an alembic migration now
        super().init_db(drop=drop)
        with Session(self.engine) as session:
            session.exec(
                insert(User)
                .values(
                    {
                        "username": "admin",
                        "password": settings.admin_password,
                        "name": "Admin",
                        "is_admin": True,
                    }
                )
                .on_conflict_do_nothing(index_elements=["username"])
            )
            session.commit()
