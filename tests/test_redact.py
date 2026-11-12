import pytest

from pakkifile.llm.redact import redact


@pytest.mark.parametrize(
    ("memo", "redacted"),
    [
        ("IBFT FROM SYN AHMED RAZA", "IBFT FROM [NAME]"),
        ("Raast P2P to Bilal Siddiqui 03001234567", "Raast P2P to [NAME] [PHONE]"),
        ("FT TO 35202-1234567-1 SAEED", "FT TO [CNIC] [NAME]"),
        ("Withdrawal to MEEZAN BANK ****4417", "Withdrawal to MEEZAN BANK [ACCOUNT]"),
        ("IBFT 0101-0104417 kiraya makaan", "IBFT [ACCOUNT] kiraya makaan"),
        ("bijli ka bill K-ELECTRIC ref 12.50", "bijli ka bill K-ELECTRIC ref [NUMBER]"),
        ("+92 300 1234567 mobile load", "[PHONE] mobile load"),
    ],
)
def test_personal_details_become_placeholders(memo: str, redacted: str) -> None:
    assert redact(memo) == redacted


def test_no_digit_survives_outside_known_memo_words() -> None:
    assert not any(ch.isdigit() for ch in redact("A1 B22 C333 4444 55555 99.99 X-9"))


@pytest.mark.parametrize("memo", ["جمع علی احمد", "IBFT FROM Müller José"])
def test_names_in_any_script_are_redacted(memo: str) -> None:
    assert redact(memo).replace("IBFT FROM ", "") == "[NAME]"


def test_known_memo_words_are_kept_in_their_own_case() -> None:
    assert redact("1LINK IBFT P2P naqd jama") == "1LINK IBFT P2P naqd jama"
