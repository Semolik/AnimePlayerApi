import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET: str = secrets.token_urlsafe(32)
    SERVER_NAME: str

    PROJECT_NAME: str

    FIRST_SUPERUSER_EMAIL: str

    POSTGRES_SCHEME: str
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    REDIS_HOST: str
    REDIS_PASSWORD: str = ""

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    SHIKIMORI_EXPIRATION_HOURS: int = 24
    titles_cache_hours: int = 6
    genres_cache_hours: int = 24 * 7
    USERS_OPEN_REGISTRATION: bool = True

    shikimori_kinds: List[str] = ["tv", "movie", "ova", "ona", "special", "tv_special",
                                  "music", "pv", "cm", "tv_13", "tv_24", "tv_48"]

    @property
    def POSTGRES_URI(self) -> PostgresDsn:
        return f"{settings.POSTGRES_SCHEME}://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"

    class Config:
        case_sensitive = True


settings = Settings()
