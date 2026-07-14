"""Typed settings. The ONLY place the API reads the environment (plan §6.2).

Profiles: local | test | staging | production. Staging/production startup
fails fast when mandatory configuration is missing or unsafe — a misconfigured
deploy must die loudly at boot, not at first request.
"""

from __future__ import annotations

import subprocess
from typing import Literal, Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from crucible.domain import BuildInfo

Profile = Literal["local", "test", "staging", "production"]

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "host.docker.internal")


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CRUCIBLE_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,  # aliased fields stay settable by field name (tests, wiring)
    )

    profile: Profile = "local"
    database_url: str = Field(
        default="postgresql+psycopg://crucible:crucible@localhost:55432/crucible",
        validation_alias=AliasChoices("CRUCIBLE_DATABASE_URL", "DATABASE_URL"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("CRUCIBLE_REDIS_URL", "REDIS_URL"),
    )
    allowed_origins: list[str] = Field(default=["http://localhost:3000"])
    git_sha: str = Field(
        default="unknown", validation_alias=AliasChoices("CRUCIBLE_GIT_SHA", "GIT_SHA")
    )
    built_at: str = Field(
        default="unknown", validation_alias=AliasChoices("CRUCIBLE_BUILT_AT", "BUILT_AT")
    )
    app_version: str = "0.1.0"

    @property
    def deployed(self) -> bool:
        return self.profile in ("staging", "production")

    @model_validator(mode="after")
    def _fail_fast_when_deployed(self) -> Self:
        if not self.deployed:
            return self
        problems: list[str] = []
        if not self.allowed_origins or "*" in self.allowed_origins:
            problems.append("allowed_origins must be an explicit non-wildcard list")
        for name, url in (("database_url", self.database_url), ("redis_url", self.redis_url)):
            if any(h in url for h in _LOCAL_HOSTS):
                problems.append(f"{name} points at a local host")
        if self.git_sha == "unknown":
            problems.append("git_sha must identify the deployed build")
        if problems:
            raise ValueError(f"unsafe {self.profile} configuration: " + "; ".join(problems))
        return self


def resolve_build_info(settings: ApiSettings) -> BuildInfo:
    """Build identity for /version. In local dev, falls back to `git rev-parse`
    so the endpoint is truthful without CI-injected metadata."""
    sha = settings.git_sha
    if sha == "unknown" and settings.profile == "local":
        try:
            sha = (
                subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=True,
                ).stdout.strip()
                or "unknown"
            )
        except Exception:
            sha = "unknown"
    return BuildInfo(
        git_sha=sha,
        version=settings.app_version,
        profile=settings.profile,
        built_at=settings.built_at,
    )
