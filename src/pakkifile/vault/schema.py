"""Local vault tables. Every record is scoped to its person (ADR-0035)."""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
)

metadata = MetaData()

person = Table(
    "person",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("role", String, nullable=False),
)

evidence_item = Table(
    "evidence_item",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("person_id", ForeignKey("person.id"), nullable=False),
    Column("file_name", String, nullable=False),
    Column("sha256", String, nullable=False),
)

statement_row = Table(
    "statement_row",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("person_id", ForeignKey("person.id"), nullable=False),
    Column("evidence_item_id", ForeignKey("evidence_item.id"), nullable=False),
    Column("row_no", Integer, nullable=False),
    Column("date", Date, nullable=False),
    Column("description", String, nullable=False),
    Column("counterparty", String),
    Column("amount_minor", BigInteger, nullable=False),
    Column("currency", String(3), nullable=False),
)
