"""The applicant's review of rows the rules and model left uncertain (ADR-0052, ADR-0056).

The applicant's decision always wins: the row takes the chosen class with source
`applicant`, and the decision is kept, beside what was proposed, as evaluation data.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Connection, insert, select, update

from pakkifile.vault.classify import RowClass
from pakkifile.vault.schema import row_correction, statement_row


class ReviewError(ValueError):
    """The row isn't this person's, or isn't waiting for review."""


@dataclass(frozen=True)
class ReviewRow:
    id: int
    booked: date
    description: str
    amount_minor: int
    currency: str
    proposed: RowClass | None
    source: str | None


def awaiting_review(conn: Connection, person_id: int) -> list[ReviewRow]:
    rows = conn.execute(
        select(
            statement_row.c.id,
            statement_row.c.date,
            statement_row.c.description,
            statement_row.c.amount_minor,
            statement_row.c.currency,
            statement_row.c.row_class,
            statement_row.c.class_source,
        )
        .where(statement_row.c.person_id == person_id, statement_row.c.needs_review)
        .order_by(statement_row.c.date, statement_row.c.id)
    ).all()
    return [ReviewRow(*row) for row in rows]


def decide(conn: Connection, person_id: int, row_id: int, chosen: RowClass, now: datetime) -> None:
    proposed = conn.execute(
        select(statement_row.c.row_class, statement_row.c.class_source).where(
            statement_row.c.id == row_id,
            statement_row.c.person_id == person_id,
            statement_row.c.needs_review,
        )
    ).first()
    if proposed is None:
        raise ReviewError(f"row {row_id} isn't waiting for this person's review")
    conn.execute(
        insert(row_correction).values(
            person_id=person_id,
            statement_row_id=row_id,
            proposed_class=proposed.row_class,
            proposed_source=proposed.class_source,
            chosen_class=chosen,
            decided_at=now,
        )
    )
    conn.execute(
        update(statement_row)
        .where(statement_row.c.id == row_id, statement_row.c.person_id == person_id)
        .values(
            row_class=chosen, class_source="applicant", class_confidence=None, needs_review=False
        )
    )
