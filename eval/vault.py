"""Score the vault on each persona's seeded evidence (brief 05, ADR-0021, ADR-0029).

Expected values come from the persona's fact table, never from the code under test. Each
persona's statements are ingested, the Meezan one as two overlapping windows, so every
transaction must be stored exactly once with its class.

    uv run python -m eval.vault

Only the dev split exists so far; a test split, with other templates and instances, waits
for the owner's review of a wider persona set.
"""

import sys
import tempfile
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Connection, select

from evaldata.meezan import write_meezan_statement
from evaldata.payoneer import write_payoneer_statement
from evaldata.persona import Persona, load_personas, month_start, transactions
from pakkifile.vault.db import vault_engine
from pakkifile.vault.ingest import add_person
from pakkifile.vault.meezan import ingest_meezan_pdf
from pakkifile.vault.payoneer import ingest_payoneer_pdf
from pakkifile.vault.schema import metadata, statement, statement_row

# Proposed to the owner with the first numbers (#37); not yet approved.
# Each score must be at least, or (for rule_wrong) at most, its gate.
PROPOSED_GATES = {
    "parse_exact": ("at least", Decimal(1)),
    "stored_once": ("at least", Decimal(1)),
    "closing_exact": ("at least", Decimal(1)),
    "rule_wrong": ("at most", Decimal(0)),
}
Key = tuple[str, date, str, int]  # account number, booking date, description, amount


@dataclass(frozen=True)
class VaultScore:
    persona: str
    expected_rows: int
    parse_exact: Decimal  # share of expected rows stored as-is, in the right account
    stored_once: Decimal  # 1 when no row is missing or stored twice
    closing_exact: Decimal  # share of accounts whose stored closing balance is the fact
    rule_right: Decimal  # share of rows the rules placed in their labelled class
    rule_ambiguous: Decimal  # share the rules left for the model
    rule_wrong: Decimal  # share the rules placed in the wrong class: worse than ambiguous


def _ratio(part: int, whole: int) -> Decimal:
    return (Decimal(part) / Decimal(whole)).quantize(Decimal("0.001")) if whole else Decimal(1)


def ingest_persona(conn: Connection, persona: Persona, out: Path) -> int:
    """Ingest a persona's evidence the way an applicant would, overlaps included.

    The Meezan statement arrives as two windows that share a month, so every row of that
    month is offered twice and must be stored once.
    """
    person = add_person(conn, "applicant")
    if "meezan" in persona.accounts:
        half = persona.months // 2
        split = month_start(persona.period_from, half)
        overlap = month_start(persona.period_from, half - 1)
        windows = ((persona.period_from, split - timedelta(days=1)), (overlap, persona.period_to))
        for start, end in windows:
            path = write_meezan_statement(persona, out / str(start), start=start, end=end)
            ingest_meezan_pdf(conn, person, path)
    if "payoneer" in persona.accounts:
        ingest_payoneer_pdf(conn, person, write_payoneer_statement(persona, out))
    return person


def score_persona(conn: Connection, persona: Persona, person: int) -> VaultScore:
    rows = conn.execute(
        select(
            statement.c.account_number,
            statement_row.c.date,
            statement_row.c.description,
            statement_row.c.amount_minor,
            statement_row.c.row_class,
        )
        .join(statement, statement.c.evidence_item_id == statement_row.c.evidence_item_id)
        .where(statement_row.c.person_id == person)
    ).all()
    facts = transactions(persona)
    want: Counter[Key] = Counter()
    labels = {}
    for t in facts:
        key = (persona.accounts[t.account].number, t.date, t.description, t.amount_minor)
        want[key] += 1
        labels[key] = t.row_class
    got: Counter[Key] = Counter()
    placed = []
    for r in rows:
        key = (r.account_number, r.date, r.description, r.amount_minor)
        got[key] += 1
        placed.append((r.row_class, labels.get(key)))
    closings = dict(
        conn.execute(
            select(statement.c.account_number, statement.c.closing_minor)
            .where(statement.c.person_id == person)
            .order_by(statement.c.period_to)  # the latest statement's closing wins
        ).all()
    )
    accounts = persona.accounts.items()
    closing_right = sum(
        closings.get(account.number) == persona.expected.closing[name] for name, account in accounts
    )
    return VaultScore(
        persona=persona.id,
        expected_rows=len(facts),
        parse_exact=_ratio(sum((want & got).values()), len(facts)),
        stored_once=Decimal(int(got == want)),
        closing_exact=_ratio(closing_right, len(accounts)),
        rule_right=_ratio(sum(cls == label for cls, label in placed), len(placed)),
        rule_ambiguous=_ratio(sum(cls is None for cls, _ in placed), len(placed)),
        rule_wrong=_ratio(
            sum(cls is not None and cls != label for cls, label in placed), len(placed)
        ),
    )


def evaluate(conn: Connection, personas: Iterable[Persona], out: Path) -> list[VaultScore]:
    return [score_persona(conn, p, ingest_persona(conn, p, out / p.id)) for p in personas]


def failures(scores: Sequence[VaultScore]) -> list[str]:
    """Each proposed gate a persona misses."""
    found = []
    for s in scores:
        for name, (bound, gate) in PROPOSED_GATES.items():
            value: Decimal = getattr(s, name)
            if (value > gate) if bound == "at most" else (value < gate):
                found.append(f"{s.persona}: {name} {value}, gate {gate}")
    return found


def _report(scores: Sequence[VaultScore]) -> Iterable[str]:
    yield "persona                   rows  parse  once  closing  rule-right  ambiguous  wrong"
    for s in scores:
        yield (
            f"{s.persona:<24} {s.expected_rows:>5}  {s.parse_exact:>5}  {s.stored_once:>4}"
            f"  {s.closing_exact:>7}  {s.rule_right:>10}  {s.rule_ambiguous:>9}  {s.rule_wrong:>5}"
        )


def main() -> None:
    engine = vault_engine()
    with engine.connect() as conn, tempfile.TemporaryDirectory() as out:
        transaction = conn.begin()
        metadata.create_all(conn)
        scores = evaluate(conn, load_personas().values(), Path(out))
        transaction.rollback()
    print("\n".join(_report(scores)))
    missed = failures(scores)
    print("\n".join(missed) or "All proposed gates pass.")
    sys.exit(1 if missed else 0)


if __name__ == "__main__":
    main()
