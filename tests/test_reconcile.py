import pytest

from pakkifile.figures.money import parse_minor
from pakkifile.figures.reconcile import BalanceRow, balance_gaps


@pytest.mark.parametrize(
    ("text", "minor"),
    [("560,000.00", 56_000_000), ("0.05", 5), ("-1,200.50", -120_050), ("12", 1200)],
)
def test_statement_amounts_parse_to_exact_minor_units(text: str, minor: int) -> None:
    assert parse_minor(text) == minor


@pytest.mark.parametrize("text", ["1.005", "1,20.00", "abc", ""])
def test_malformed_amounts_are_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        parse_minor(text)


ROWS = [BalanceRow(1, 500, 0, 1500), BalanceRow(2, 0, 200, 1300)]


def test_balances_that_add_up_have_no_gaps() -> None:
    assert balance_gaps(1000, ROWS, 1300) == []


def test_a_wrong_running_balance_names_its_row_and_the_difference() -> None:
    rows = [ROWS[0], BalanceRow(2, 0, 200, 1250)]
    assert balance_gaps(1000, rows, 1250) == ["row 2: balance 1250, expected 1300 (off by -50)"]


def test_a_wrong_closing_balance_is_reported() -> None:
    assert balance_gaps(1000, ROWS, 1400) == ["closing balance 1400, expected 1300 (off by 100)"]
