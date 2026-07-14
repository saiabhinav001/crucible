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
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("CRUCIBLE_REDIS_URL", "REDIS_URL"),
    )
    git_sha: str = Field(
        default="unknown", validation_alias=AliasChoices("CRUCIBLE_GIT_SHA", "GIT_SHA")
    )
    job_concurrency: int = 4
