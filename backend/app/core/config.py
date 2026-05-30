from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = (
        "postgresql+psycopg2://medfabric:changeme@localhost:5432/medfabric"
    )

    # JWT
    jwt_secret_key: str = "INSECURE_DEFAULT_CHANGE_ME"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    refresh_token_expire_hours: int = 12

    # Storage
    dataset_root: Path = Path("/data/datasets")

    # Admin bootstrap
    admin_usernames: List[str] = ["admin"]

    # Registration — leave empty to disable self-registration
    registration_code: str = ""

    # App
    app_title: str = "MedFabric"
    app_version: str = "3.0.0-alpha"
    log_level: str = "INFO"
    expose_api_docs: bool = True
    docker_version: str = ""  # optional; set via DOCKER_VERSION env var

    @property
    def refresh_token_expire_seconds(self) -> int:
        return self.refresh_token_expire_hours * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
