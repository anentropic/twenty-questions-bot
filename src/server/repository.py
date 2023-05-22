import logging

from alembic.config import Config
from alembic import command
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session

from twentyqs.repository import Repository as BaseRepository, User
from .config import settings

logger = logging.getLogger(__name__)


def safe_migrate(alembic_cfg_path: str):
    """
    SQLite doesn't have transactional DDL, so if a migration fails
    the database can be in an inconsistent state. In this case we may
    recover by downgrading and re-upgrading.

    (This won't help if the current migration is buggy of course)
    """
    alembic_cfg = Config(alembic_cfg_path)
    alembic_cfg.attributes["configure_logger"] = False
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        logger.error(f"Failed to migrate: {e!r}")
        logger.info("Attempting to downgrade and re-upgrade...")
        command.downgrade(alembic_cfg, "-1")
        command.upgrade(alembic_cfg, "head")


class Repository(BaseRepository):
    def init_db(self, drop=False):
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
