"""Where the local vault database is: the one place that knows (ADR-0035)."""

import os

from sqlalchemy import Engine, create_engine

from pakkifile.vault.schema import metadata

DEFAULT_URL = "postgresql+psycopg://pakkifile:pakkifile@127.0.0.1:5433/pakkifile"


def vault_engine() -> Engine:
    """The vault's database, from PAKKIFILE_DATABASE_URL or the local default."""
    return create_engine(os.environ.get("PAKKIFILE_DATABASE_URL", DEFAULT_URL))


def open_vault() -> Engine:
    """The vault's database with its tables. Only missing tables are created: migrations wait
    for the first local release (ADR-0055)."""
    engine = vault_engine()
    metadata.create_all(engine)
    return engine
