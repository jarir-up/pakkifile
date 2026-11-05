"""Continuity figures (M2): credits the vault cannot attribute to a counterparty."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Connection, text

from pakkifile.figures.money import ROUNDING, Money


@dataclass(frozen=True)
class SourceRow:
    file_name: str
    row_no: int
    date: date
    description: str


@dataclass(frozen=True)
class UnattributedCredit:
    amount: Money
    share_of_credits: Decimal
    rows: tuple[SourceRow, ...]


_LARGEST_UNATTRIBUTED = text("""
    WITH credits AS (
        SELECT r.*, e.file_name FROM statement_row r
        JOIN evidence_item e ON e.id = r.evidence_item_id
        WHERE r.evidence_item_id = :item AND r.amount_minor > 0
    )
    SELECT file_name, row_no, date, description, amount_minor, currency,
           round(amount_minor::numeric / (SELECT sum(amount_minor) FROM credits), 4) AS share
    FROM credits
    WHERE counterparty IS NULL
    ORDER BY amount_minor DESC, row_no
    LIMIT 1
""")


def largest_unattributed_credit(
    conn: Connection, evidence_item_id: int
) -> UnattributedCredit | None:
    row = conn.execute(_LARGEST_UNATTRIBUTED, {"item": evidence_item_id}).one_or_none()
    if row is None:
        return None
    return UnattributedCredit(
        amount=Money(row.amount_minor, row.currency),
        share_of_credits=row.share,
        rows=(SourceRow(row.file_name, row.row_no, row.date, row.description),),
    )


def format_share(share: Decimal) -> str:
    return f"{(share * 100).quantize(Decimal('0.1'), rounding=ROUNDING)}%"
