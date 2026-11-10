from decimal import Decimal
from itertools import accumulate

import pytest

from evaldata.persona import _minor, load_personas, transactions

PERSONAS = load_personas()


def test_three_synthetic_personas_load() -> None:
    assert set(PERSONAS) == {"syn-dev-payoneer", "syn-designer-direct", "syn-student-sponsored"}
    for key, persona in PERSONAS.items():
        assert persona.id == key and key.startswith("syn-")  # R-28
        assert persona.seeds


def test_every_monthly_line_has_one_amount_per_month() -> None:
    for persona in PERSONAS.values():
        for line in persona.monthly:
            assert (line.amount is None) != (line.amounts is None), line.description
            assert line.amounts is None or len(line.amounts) == persona.months
            assert line.day is not None and line.booked is None


def test_no_account_ever_goes_below_zero() -> None:
    for persona in PERSONAS.values():
        for name, account in persona.accounts.items():
            rows = [t.amount_minor for t in transactions(persona) if t.account == name]
            assert min(accumulate(rows, initial=account.opening)) >= 0, (persona.id, name)


def test_each_payoneer_withdrawal_arrives_at_the_bank_at_the_persona_rate() -> None:
    for persona in PERSONAS.values():
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
