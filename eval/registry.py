"""Evaluate computed confidence against hand-judged ordering (brief 02).

Every pair of requirements in different hand-labelled tiers must be ordered
the same way by computed confidence. Exits non-zero below 1.0.

    uv run python -m eval.registry
"""

import sys
from datetime import date
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

from pakkifile.registry.confidence import confidence
from pakkifile.registry.files import load_registry
from pakkifile.registry.publish import publish_status

LABELS = Path("evaldata/labels/confidence-order.yaml")
AS_OF = date(2026, 10, 30)


def ordering_agreement() -> Decimal:
    registry = load_registry(Path("registry-data"))

    def score(label: dict[str, Any]) -> Decimal:
        entry = next(
            e
            for e in registry.entries
            if e.authority.name == label["authority"] and e.application.purpose == label["purpose"]
        )
        req = next(r for r in entry.requirements if r.id == label["id"])
        return confidence(req, registry.sources, AS_OF).score

    tiers = [[score(label) for label in tier] for tier in yaml.safe_load(LABELS.read_text())]
    pairs = [(hi, lo) for upper, lower in combinations(tiers, 2) for hi in upper for lo in lower]
    agreed = sum(1 for hi, lo in pairs if hi > lo)
    return Decimal(agreed) / len(pairs)


def needs_review() -> list[str]:
    registry = load_registry(Path("registry-data"))
    return [
        f"{e.authority.name} / {e.application.label} / {r.id}"
        for e in registry.entries
        for r in e.requirements
        if publish_status(r, registry.sources, AS_OF) == "needs_review"
    ]


def main() -> None:
    agreement = ordering_agreement()
    passed = agreement == 1
    print(f"{'PASS' if passed else 'FAIL'}  confidence ordering agreement {agreement:.2f}")
    for item in needs_review():
        print(f"REVIEW  {item}")
    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
