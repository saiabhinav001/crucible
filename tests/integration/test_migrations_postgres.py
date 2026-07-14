"""Applies migrations to a real empty Postgres (compose or CI service).

Skips cleanly when Postgres is unreachable so `pytest` stays green on a
machine without the stack; CI runs it with services and DATABASE_URL set.
"""

import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://crucible:crucible@localhost:55432/crucible"
)


def _reachable() -> bool:
    try:
        engine = sa.create_engine(DATABASE_URL, connect_args={"connect_timeout": 3})
        with engine.connect():
            return True
    except Exception:
        return False


requires_pg = pytest.mark.skipif(not _reachable(), reason="Postgres not reachable")


@requires_pg
def test_upgrade_head_on_live_database() -> None:
    cfg = Config(str(REPO_ROOT / "packages" / "db" / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")

    engine = sa.create_engine(DATABASE_URL)
    with engine.connect() as conn:
        version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
        assert version == "0001"
        ext = conn.execute(
            sa.text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
        assert ext == 1


@requires_pg
def test_downgrade_base_is_reversible() -> None:
    cfg = Config(str(REPO_ROOT / "packages" / "db" / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")  # leave the database migrated for other tests
