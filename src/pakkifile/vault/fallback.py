"""Send the rows the rules couldn't place to the local model, after ingestion (ADR-0056).

A statement is stored without Ollama running; this pass runs whenever the model is there.
Every row still waits for the applicant; the review page lists the uncertain ones first.
"""

from sqlalchemy import Connection, select, update

from pakkifile.llm.classify_row import classify_memo
from pakkifile.llm.ollama import LocalModel
from pakkifile.vault.classify import Direction
from pakkifile.vault.schema import statement_row


def classify_pending(conn: Connection, person_id: int, model: LocalModel) -> int:
    """Classify this person's rows no rule, model or applicant has classified yet."""
    pending = conn.execute(
        select(statement_row.c.id, statement_row.c.description, statement_row.c.amount_minor)
        .where(
            statement_row.c.person_id == person_id,
            statement_row.c.class_source.is_(None),
        )
        .order_by(statement_row.c.id)
    ).all()
    for row in pending:
        direction: Direction = "credit" if row.amount_minor > 0 else "debit"
        result = classify_memo(row.description, direction, model)
        conn.execute(
            update(statement_row)
            .where(statement_row.c.id == row.id)
            .values(
                row_class=result.row_class,
                class_source="model",
                class_confidence=result.confidence,
            )
        )
    return len(pending)
