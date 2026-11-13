"""Local vault tables. Every record is scoped to its person (ADR-0035)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
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

# ADR-0056: each review decision, kept as evaluation data. It never leaves the machine.
row_correction = Table(
    "row_correction",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("person_id", ForeignKey("person.id"), nullable=False),
    Column("statement_row_id", ForeignKey("statement_row.id"), nullable=False),
    Column("proposed_class", String),  # null when nothing could place the row
    Column("proposed_source", String),
    Column("chosen_class", String, nullable=False),
    Column("decided_at", DateTime(timezone=True), nullable=False),
)

# ADR-0057, ADR-0058: one row per remittance an e-PRC or S-PRC proves. Figures are kept as
# printed and never used for arithmetic (R-20); the foreign amount and the rate may be absent
# (owner, 2026-11-13). statement_row_id is null until a credit matches.
prc_certificate = Table(
    "prc_certificate",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("person_id", ForeignKey("person.id"), nullable=False),
    Column("evidence_item_id", ForeignKey("evidence_item.id"), nullable=False),
    Column("certificate_no", String, nullable=False),
    Column("issued", Date, nullable=False),
    Column("remitter", String, nullable=False),
    Column("realized", Date, nullable=False),  # the date of realization (ADR-0058)
    Column("foreign_minor", BigInteger),
    Column("foreign_currency", String(3)),
    Column("rate", Numeric),
    Column("pkr_minor", BigInteger, nullable=False),
    Column("purpose", String, nullable=False),
    Column("statement_row_id", ForeignKey("statement_row.id")),
)
