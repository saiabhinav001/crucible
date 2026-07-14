"""Typed worker settings — the only place the worker reads the environment."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerAppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CRUCIBLE_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    profile: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = Field(
        default="postgresql+psycopg://crucible:crucible@localhost:55432/crucible",
        validation_alias=AliasChoices("CRUCIBLE_DATABASE_URL", "DATABASE_URL"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("CRUCIBLE_REDIS_URL", "REDIS_URL"),
    )
    git_sha: str = Field(
        default="unknown", validation_alias=AliasChoices("CRUCIBLE_GIT_SHA", "GIT_SHA")
    )
    job_concurrency: int = 4

    s3_bucket: str = Field(default="crucible-local", validation_alias=AliasChoices("S3_BUCKET"))
    s3_endpoint_url: str | None = Field(
        default="http://localhost:9000", validation_alias=AliasChoices("S3_ENDPOINT_URL")
    )
    s3_region: str = Field(default="us-east-1", validation_alias=AliasChoices("S3_REGION"))
    # The worker only reads objects server-side; it never issues presigned URLs.
    s3_access_key: str | None = Field(
        default="crucible", validation_alias=AliasChoices("S3_ACCESS_KEY")
    )
    s3_secret_key: str | None = Field(
        default="crucible-local-only", validation_alias=AliasChoices("S3_SECRET_KEY")
    )
