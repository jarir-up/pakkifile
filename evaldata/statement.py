"""Seeded synthetic bank statements driven by a fact table (ADR-0021).

The fact table fixes every amount that matters to an evaluation; the seed only
varies dates within a month, reference numbers and everyday debits.
"""

import csv
import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

COLUMNS = ["row_id", "date", "description", "amount_minor", "currency", "synthetic"]


@dataclass(frozen=True)
class Remittance:
    month: date
    client: str
    amount_minor: int


@dataclass(frozen=True)
class StatementFacts:
    persona: str
    currency: str
    remittances: tuple[Remittance, ...]
    cash_deposit: tuple[date, int] | None
    tuition_payment: tuple[date, int]


TRACER_FACTS = StatementFacts(
    persona="syn-freelancer-01",
    currency="PKR",
    remittances=tuple(
        Remittance(date(2026, m, 1), "CLIENT ALPHA GMBH", 25_000_000) for m in range(4, 10)
    ),
    cash_deposit=(date(2026, 9, 12), 90_000_000),
    tuition_payment=(date(2026, 9, 15), 110_000_000),
)

# Hand-computed: PKR 900,000 of PKR 2,400,000 credits.
TRACER_EXPECTED_SHARE = Decimal("0.3750")


def write_statement(facts: StatementFacts, seed: int, out_dir: Path) -> Path:
    """Write the statement CSV and return its path."""
    rng = random.Random(seed)
    entries: list[tuple[date, str, int]] = []
    for r in facts.remittances:
        day = r.month.replace(day=rng.randint(2, 9))
        entries.append(
            (
                day,
                f"HOME REMITTANCE - {r.client} - PRC {rng.randint(100000, 999999)}",
                r.amount_minor,
            )
        )
        rent_day = r.month.replace(day=rng.randint(10, 14))
        entries.append((rent_day, "IBFT RENT", -rng.randint(40_000, 60_000) * 100))
    if facts.cash_deposit:
        deposit_day, deposit = facts.cash_deposit
        entries.append((deposit_day, "CASH DEPOSIT", deposit))
    tuition_day, tuition = facts.tuition_payment
    entries.append((tuition_day, "IBFT SYN HOCHSCHULE TUITION FEE", -tuition))
    entries.sort(key=lambda e: (e[0], e[1]))

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{facts.persona}-statement-synthetic.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for row_id, (day, description, amount) in enumerate(entries, start=1):
            writer.writerow([row_id, day.isoformat(), description, amount, facts.currency, "true"])
    return path
