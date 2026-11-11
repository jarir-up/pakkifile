import pytest

from evaldata.persona import load_personas, transactions
from pakkifile.vault.classify import AccountKind, classify

SPONSORS = ("SYN TARIQ MAHMOOD",)


@pytest.mark.parametrize(
    ("description", "amount", "expected"),
    [
        ("HOME REMITTANCE PAYONEER INC PRC 4471", 56_000_000, "remittance_in"),
        ("INWARD SWIFT SYN FJORD DESIGN AS", 42_000_000, "remittance_in"),
        ("IBFT FROM SYN TARIQ MAHMOOD", 15_000_000, "sponsor_transfer"),
        ("Raast transfer from abbu", 5_000_000, "sponsor_transfer"),
        ("CASH DEPOSIT", 35_000_000, "cash_deposit"),
        ("IBFT kiraya makaan", -6_500_000, "spending"),
        ("bijli ka bill K-ELECTRIC", -1_450_000, "spending"),
        ("IBFT to own JAZZCASH wallet", -2_000_000, "own_transfer"),
        ("WITHHOLDING TAX 236P", -120_000, "tax"),
        ("Payment from SYN NORTHWIND LLC via Upwork", 210_000, "client_payment"),
        ("Withdrawal to MEEZAN BANK ****4417", -200_000, "platform_withdrawal"),
        ("Annual account fee", -2_995, "fee"),
        ("naqd jama", 2_000_000, "cash_deposit"),
        ("WHT ON PROFIT", -5_000, "tax"),
        ("BANK CHARGES", -15_000, "fee"),
        ("SMS ALERT FEE", -5_000, "fee"),
        ("mobile load JAZZ", -200_000, "spending"),
    ],
)
def test_rules_place_common_memos(description: str, amount: int, expected: str) -> None:
    account: AccountKind = (
        "platform" if expected in ("client_payment", "platform_withdrawal") else "bank"
    )
    assert classify(description, amount, account, SPONSORS).row_class == expected


@pytest.mark.parametrize(
    "description",
    [
        "IBFT 0093 REF 22817",
        "INWARD IBFT FROM SYN BILAL",  # domestic, not a foreign remittance
        "IBFT FROM WALID KHAN",  # a name, not "parent"
        "FROM SYN KHALIDA",  # contains the sponsor-like "ALI" but is not them
    ],
)
def test_a_memo_no_rule_knows_is_ambiguous(description: str) -> None:
    result = classify(description, 1_000_000, "bank", ("SYN ALI",))
    assert result.row_class is None and result.rules == ()


def test_two_rules_that_disagree_make_a_row_ambiguous() -> None:
    # A cash deposit naming the sponsor: cash, or the sponsor's money? Rules don't guess.
    result = classify("CASH DEPOSIT BY SYN TARIQ MAHMOOD", 1_000_000, "bank", SPONSORS)
    assert result.row_class is None and len(result.rules) == 2


def test_direction_matters_a_credit_is_never_spending() -> None:
    assert classify("IBFT kiraya makaan", 6_500_000, "bank", SPONSORS).row_class is None


def test_platform_rows_are_only_read_on_platform_statements() -> None:
    assert classify("PAYMENT FROM SYN ANYONE", 1_000_000, "bank").row_class is None
    assert classify("Withdrawal to bank", -1_000_000, "bank").row_class is None


def test_every_persona_row_gets_its_labelled_class() -> None:
    # The personas are the dev split (ADR-0029); a held-out split is still to be written.
    for persona in load_personas().values():
        sponsors = ("SYN TARIQ MAHMOOD",) if persona.id == "syn-student-sponsored" else ()
        for t in transactions(persona):
            account: AccountKind = "platform" if t.account == "payoneer" else "bank"
            got = classify(t.description, t.amount_minor, account, sponsors).row_class
            assert got == t.row_class, (persona.id, t.description)
