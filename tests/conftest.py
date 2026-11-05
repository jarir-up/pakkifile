import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, create_engine

from pakkifile.vault.schema import metadata

DEFAULT_URL = "postgresql+psycopg://pakkifile:pakkifile@127.0.0.1:5433/pakkifile"


@pytest.fixture
def db() -> Iterator[Connection]:
    """A real Postgres connection, rolled back after each test.

    Start it with `docker compose up -d --wait db`.
    """
    engine = create_engine(os.environ.get("PAKKIFILE_DATABASE_URL", DEFAULT_URL))
    with engine.connect() as conn:
        transaction = conn.begin()
        metadata.create_all(conn)
        yield conn
        transaction.rollback()
    engine.dispose()
