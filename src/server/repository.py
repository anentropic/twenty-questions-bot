from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session

from twentyqs.repository import Repository as BaseRepository, User
from .config import get_settings


class Repository(BaseRepository):
    def init_db(self, drop=False):
        super().init_db(drop=drop)
        with Session(self.engine) as session:
            session.exec(
                insert(User)
                .values(
                    {
                        "username": "admin",
                        "password": get_settings().admin_password,
                        "name": "Admin",
                        "is_admin": True,
                    }
                )
                .on_conflict_do_nothing(index_elements=["username"])
            )
            session.commit()
