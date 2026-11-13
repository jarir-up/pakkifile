from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, text

from pakkifile.vault.db import vault_engine
from pakkifile.vault.schema import metadata


@pytest.fixture
def db() -> Iterator[Connection]:
    """A real Postgres connection, rolled back after each test.

    Start it with `docker compose up -d --wait db`.
    """
    engine = vault_engine()
    with engine.connect() as conn:
        transaction = conn.begin()
        # A schema of its own, gone at rollback: tests never see or depend on the local
        # vault's tables, whatever they hold or however old their shape.
        conn.execute(text("CREATE SCHEMA pakkifile_test"))
        conn.execute(text("SET LOCAL search_path TO pakkifile_test"))
        metadata.create_all(conn)
        yield conn
        transaction.rollback()
    engine.dispose()
