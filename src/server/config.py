import secrets

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    openai_model: str = "gpt-3.5-turbo"
    simple_subject_picker: bool = True
    db_path: str = "twentyqs.db"
    alembic_config: str = "alembic.ini"
    migrate_db: bool = True
    # require_login: bool = True
    log_level: str = "INFO"
    verbose_langchain: bool = False
    admin_password: str
    secret_key: str = Field(default_factory=secrets.token_urlsafe)


settings = Settings()
