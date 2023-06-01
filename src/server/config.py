import secrets

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """
    Specify these via environment variables or a .env file.

    Also implicitly required:
    - OPENAI_API_KEY
    """

    db_path: str = "twentyqs.db"
    alembic_config: str = "alembic.ini"
    migrate_db: bool = True

    log_level: str = "INFO"

    openai_model: str = "gpt-3.5-turbo"
    simple_subject_picker: bool = True
    verbose_langchain: bool = False

    admin_password: str
    # will be used to sign cookies, logins will be invalidated on each restart
    # unless you supply a value here:
    secret_key: str = Field(default_factory=secrets.token_urlsafe)
    # require_login: bool = True

    # only needed if pushing played games data to HF dataset from admin site
    hf_repo_id: str = "twenty-questions-bot"
    hf_api_token: str = "dummy"


settings = Settings()
