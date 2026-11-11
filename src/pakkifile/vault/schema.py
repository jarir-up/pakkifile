"""Local vault tables. Every record is scoped to its person (ADR-0035)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    Float,
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

statement = Table(
    "statement",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("person_id", ForeignKey("person.id"), nullable=False),
    Column("evidence_item_id", ForeignKey("evidence_item.id"), nullable=False, unique=True),
    Column("account_title", String, nullable=False),
    Column("account_number", String, nullable=False),
    Column("iban", String),
    Column("currency", String(3), nullable=False),
    Column("period_from", Date, nullable=False),
    Column("period_to", Date, nullable=False),
    Column("opening_minor", BigInteger, nullable=False),
    Column("closing_minor", BigInteger, nullable=False),
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
    Column("balance_minor", BigInteger),
    # Kept but flagged: same account, day and amount as this row, described differently.
    Column("possible_duplicate_of", ForeignKey("statement_row.id")),
    Column("fingerprint", String),  # stable key when there is no transaction ID (ADR-0028)
    # ADR-0056: null while unclassified; the source is rule, model or applicant.
    Column("row_class", String),
    Column("class_source", String),
    Column("class_confidence", Float),  # the model's, 0 to 1; null for rules and the applicant
    Column("needs_review", Boolean, nullable=False),
)
