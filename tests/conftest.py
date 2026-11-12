from collections.abc import Iterator

import pytest
from sqlalchemy import Connection

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
        metadata.create_all(conn)
        yield conn
        transaction.rollback()
    engine.dispose()
