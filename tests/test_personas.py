from decimal import Decimal
from itertools import accumulate

import pytest

from evaldata.persona import MonthlyLine, _minor, load_personas, transactions

ALL = load_personas()


def test_three_synthetic_personas_load() -> None:
    assert set(ALL) == {"syn-dev-payoneer", "syn-designer-direct", "syn-student-sponsored"}
    for key, persona in ALL.items():
        assert persona.id == key and key.startswith("syn-")  # R-28
        assert persona.seeds


def test_a_monthly_line_needs_exactly_one_amount_form() -> None:
    line = {"account": "meezan", "description": "x", "class": "fee", "day": 1}
    with pytest.raises(ValueError, match="amount or amounts"):
        MonthlyLine.model_validate(line)
    with pytest.raises(ValueError, match="amount or amounts"):
        MonthlyLine.model_validate({**line, "amount": "1", "amounts": ["1"]})


def test_expected_figures_agree_with_the_lines() -> None:
    # Checks the hand-worked figures against the lines, independently of `figures`.
    for persona in ALL.values():
        rows = transactions(persona)
        expected = persona.expected
        for name, account in persona.accounts.items():
            total = account.opening + sum(t.amount_minor for t in rows if t.account == name)
            assert expected.closing[name] == total, (persona.id, name)
        by_class = {
            c: sum(t.amount_minor for t in rows if t.row_class == c)
            for c in ("remittance_in", "sponsor_transfer")
        }
        assert expected.remittances_in_pkr == by_class["remittance_in"], persona.id
        assert expected.sponsor_transfers_pkr == by_class["sponsor_transfer"], persona.id
        cash = [t.amount_minor for t in rows if t.row_class == "cash_deposit"]
        assert expected.largest_unattributed_credit_pkr == (max(cash) if cash else None)


def test_no_account_ever_goes_below_zero() -> None:
    for persona in ALL.values():
        for name, account in persona.accounts.items():
            rows = [t.amount_minor for t in transactions(persona) if t.account == name]
            assert min(accumulate(rows, initial=account.opening)) >= 0, (persona.id, name)


def test_each_payoneer_withdrawal_arrives_at_the_bank_at_the_persona_rate() -> None:
    for persona in ALL.values():
        rows = transactions(persona)
        withdrawals = [t for t in rows if t.row_class == "platform_withdrawal"]
        arrivals = [t for t in rows if "PAYONEER" in t.description and t.account == "meezan"]
        assert len(withdrawals) == len(arrivals)
        for out, arrived in zip(withdrawals, arrivals, strict=True):
            assert Decimal(-out.amount_minor) * persona.usd_pkr == arrived.amount_minor
            assert out.date < arrived.date


def test_amounts_are_exact_minor_units() -> None:
    assert _minor("1,800.50") == 180050
    with pytest.raises(ValueError, match="two decimal places"):
        _minor("1.005")
