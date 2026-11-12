"""Where the local vault database is: the one place that knows (ADR-0035)."""

import os

from sqlalchemy import Engine, create_engine

DEFAULT_URL = "postgresql+psycopg://pakkifile:pakkifile@127.0.0.1:5433/pakkifile"


def vault_engine() -> Engine:
    """The vault's database, from PAKKIFILE_DATABASE_URL or the local default."""
    return create_engine(os.environ.get("PAKKIFILE_DATABASE_URL", DEFAULT_URL))
