from datetime import date
from decimal import Decimal

from pakkifile.figures.continuity import SourceRow, UnattributedCredit
from pakkifile.figures.money import Money
from pakkifile.mismatch.continuity import check_unattributed_credit
from tests.helpers import islamabad_study

TUITION = next(
    r for r in islamabad_study().requirements if r.id == "proof-of-payment-of-tuition-fees"
)
ROW = SourceRow("statement-synthetic.csv", 14, date(2026, 9, 12), "CASH DEPOSIT")


def _credit(share: str) -> UnattributedCredit:
    return UnattributedCredit(Money(90_000_000, "PKR"), Decimal(share), (ROW,))


def test_large_unattributed_credit_is_an_m2_finding_on_the_requirement() -> None:
    finding = check_unattributed_credit(_credit("0.3750"), TUITION)
    assert finding is not None
    assert finding.kind == "M2"
    assert finding.requirement is TUITION
    assert "PKR 900,000" in finding.statement
    assert "37.5%" in finding.statement
    assert "2026-09-12" in finding.statement


def test_small_unattributed_credit_is_not_a_finding() -> None:
    assert check_unattributed_credit(_credit("0.1000"), TUITION) is None


def test_no_unattributed_credit_is_not_a_finding() -> None:
    assert check_unattributed_credit(None, TUITION) is None


def test_finding_never_advises_concealment() -> None:
    finding = check_unattributed_credit(_credit("0.3750"), TUITION)
    assert finding is not None
    for word in ("hide", "remove", "avoid", "approv", "refus", "chance"):
        assert word not in finding.statement.lower()
