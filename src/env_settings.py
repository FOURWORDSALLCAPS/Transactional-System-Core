from functools import cached_property
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DjangoSettings(BaseModel):
    SECRET_KEY: NonEmptyStr
    DEBUG: bool = Field(
        default=False,
        description="Disabled by default to protect admin from credentials leak on production environment "
        "when env param get wrong value. That happends because of param name typos "
        "and another common configuration mistakes.",
    )
    ALLOWED_HOSTS: list[str] = ["127.0.0.1", "localhost"]
    CSRF_TRUSTED_ORIGINS: list[str] = Field(
        default=[],
        description="Trusted origins for CSRF checks.",
    )

    STATIC_URL: str = "static/"
    MEDIA_URL: str = "media/"

    @field_validator("ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS", mode="before")
    @classmethod
    def parse_comma_separated(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        return [item.strip() for item in value.split(",") if item]


class EnvSettings(BaseSettings):
    DJ: DjangoSettings = Field(default_factory=DjangoSettings)

    POSTGRES_USER: str = "postgres_user"
    POSTGRES_PASSWORD: str = "postgres_password"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "postgres_db"
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 5

    model_config = SettingsConfigDict(
        env_file="src/.env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        validate_default=True,
        ignored_types=(cached_property,),
        extra="forbid",
    )

    @property
    def get_postgres_uri(self):
        return f"psql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
