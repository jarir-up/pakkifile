import re
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Connection, func, select

from evaldata.payoneer import write_payoneer_statement
from evaldata.pdf import amount_text
from evaldata.persona import Persona, load_personas, transactions
from pakkifile.vault import statements
from pakkifile.vault.ingest import add_person
from pakkifile.vault.payoneer import account_name, ingest_payoneer_pdf, parse_payoneer
from pakkifile.vault.schema import evidence_item, statement, statement_row
from pakkifile.vault.statements import StatementError, pdf_text

ALL = load_personas()
WITH_PAYONEER = [p for p in ALL.values() if "payoneer" in p.accounts]


def _rows(persona: Persona) -> list[tuple[str, int]]:
    return [
        (t.description, t.amount_minor) for t in transactions(persona) if t.account == "payoneer"
    ]


@pytest.mark.parametrize("persona", WITH_PAYONEER, ids=lambda p: p.id)
def test_every_row_and_header_field_reads_back_exactly(persona: Persona, tmp_path: Path) -> None:
    parsed = parse_payoneer(pdf_text(write_payoneer_statement(persona, tmp_path)))
    account = persona.accounts["payoneer"]
    assert (parsed.account_title, parsed.account_number) == (
        account.holder,
        account_name(account.currency),
    )
    assert parsed.currency == account.currency
    assert (parsed.period_from, parsed.period_to) == (persona.period_from, persona.period_to)
    assert parsed.opening_minor == account.opening
    assert parsed.closing_minor == persona.expected.closing["payoneer"]
    got = [(r.description, r.credit_minor - r.debit_minor) for r in parsed.rows]
    assert got == _rows(persona)
    want_dates = [t.date for t in transactions(persona) if t.account == "payoneer"]
    assert [r.booked for r in parsed.rows] == want_dates


def test_a_long_description_wraps_and_is_joined_back(tmp_path: Path) -> None:
    persona = ALL["syn-dev-payoneer"]
    parsed = parse_payoneer(pdf_text(write_payoneer_statement(persona, tmp_path)))
    assert "Payment from SYN NORTHWIND LLC via Upwork" in [r.description for r in parsed.rows]


def test_a_statement_over_several_pages_reads_every_row(tmp_path: Path) -> None:
    dev = ALL["syn-dev-payoneer"]
    monthly = [
        line.model_copy(update={"amounts": line.amounts * 6}) if line.amounts else line
        for line in dev.monthly
    ]
    long = dev.model_copy(update={"months": 36, "monthly": monthly})
    parsed = parse_payoneer(pdf_text(write_payoneer_statement(long, tmp_path)))
    assert len(parsed.rows) == len(_rows(long)) > 70


def test_running_balances_that_do_not_add_up_stop_ingestion(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_payoneer_statement(ALL["syn-dev-payoneer"], tmp_path)
    text = pdf_text(path)
    third = parse_payoneer(text).rows[2].balance_minor
    shown, raised = amount_text(third), amount_text(third + 100)
    tampered = re.sub(rf"(?<![\d,]){re.escape(shown)}\b", raised, text, count=1)
    monkeypatch.setattr(statements, "pdf_text", lambda *_: tampered)
    person = add_person(db, "applicant")
    with pytest.raises(StatementError, match=r"row 3: .*\(off by 100\)"):
        ingest_payoneer_pdf(db, person, path)
    assert db.scalar(select(func.count()).where(evidence_item.c.person_id == person)) == 0


def test_ingest_stores_rows_in_the_account_currency_with_platform_classes(
    db: Connection, tmp_path: Path
) -> None:
    persona = ALL["syn-dev-payoneer"]
    item = ingest_payoneer_pdf(
        db, add_person(db, "applicant"), write_payoneer_statement(persona, tmp_path)
    )
    stored = db.execute(select(statement).where(statement.c.evidence_item_id == item)).one()
    assert (stored.currency, stored.closing_minor) == ("USD", persona.expected.closing["payoneer"])
    rows = db.execute(
        select(statement_row.c.currency, statement_row.c.row_class).where(
            statement_row.c.evidence_item_id == item
        )
    ).all()
    labels = [t.row_class for t in transactions(persona) if t.account == "payoneer"]
    assert len(rows) == len(labels)
    assert {r.currency for r in rows} == {"USD"}
    assert sorted(str(r.row_class) for r in rows) == sorted(labels)


def test_a_statement_with_no_rows_is_refused_since_its_balance_is_unknown() -> None:
    header = (
        "SYN HOLDER                       Account USD balance\n"
        "SYN ADDRESS                      Period 04/01/2026 - 04/30/2026\n"
        "                                 Issuing Date 05/01/2026\n"
        "Date        Description        Amount    Status    Running Balance\n"
    )
    with pytest.raises(StatementError, match="no transactions"):
        parse_payoneer(header)


def test_a_row_not_completed_stops_ingestion_rather_than_count_its_money(
    tmp_path: Path,
) -> None:
    text = pdf_text(write_payoneer_statement(ALL["syn-dev-payoneer"], tmp_path))
    with pytest.raises(StatementError, match="Pending"):
        parse_payoneer(text.replace("Completed", "Pending  ", 1))


def test_unknown_text_after_the_table_stops_rather_than_join_a_description(
    tmp_path: Path,
) -> None:
    text = pdf_text(write_payoneer_statement(ALL["syn-dev-payoneer"], tmp_path))
    footer = "      Synthetic platform footer, not part of any row"
    with pytest.raises(StatementError, match="unreadable row: Synthetic platform footer"):
        parse_payoneer(text.replace("Page 1 of 1", f"{footer}\nPage 1 of 1"))


# The real row shape (owner, 2026-11-12), values replaced: newest first, the amount with its
# currency, a status only on some rows, the running balance last.
REAL_ROWS = """SYN HOLDER                                      Account USD balance
SYN ADDRESS                                     Period 02/01/2024 - 02/29/2024
SYN CITY 00000                                  Issuing Date 03/01/2024
0000000000
Date          Description                              Amount       Status      Running Balance
27 Feb, 2024  Payment from SYN CLIENT Inc.             188.40 USD                    454.20
21 Feb, 2024  Withdrawal to SYN BANK (0000)            -150.00 USD  Completed        265.80
21 Feb, 2024  Payment from SYN CLIENT Inc.             412.50 USD                    415.80
19 Feb, 2024  Payment from SYN CLIENT Inc.             3.30 USD                        3.30
"""


def test_the_real_row_layout_reads_oldest_first() -> None:
    parsed = parse_payoneer(REAL_ROWS)
    assert [(r.row_no, r.booked.day, r.credit_minor - r.debit_minor) for r in parsed.rows] == [
        (1, 19, 330),
        (2, 21, 41_250),
        (3, 21, -15_000),
        (4, 27, 18_840),
    ]
    assert (parsed.opening_minor, parsed.closing_minor) == (0, 45_420)
    assert parsed.rows[2].description == "Withdrawal to SYN BANK (0000)"


def test_a_row_in_another_currency_stops_the_parse() -> None:
    with pytest.raises(StatementError, match="GBP"):
        parse_payoneer(REAL_ROWS.replace("188.40 USD", "188.40 GBP"))


def test_rows_printed_oldest_first_stop_the_parse() -> None:
    header, table = REAL_ROWS.split("Running Balance\n")
    oldest_first = "\n".join(reversed(table.strip().splitlines()))
    with pytest.raises(StatementError, match="oldest first"):
        parse_payoneer(f"{header}Running Balance\n{oldest_first}\n")


def test_a_statement_without_its_table_header_says_so() -> None:
    with pytest.raises(StatementError, match=r"no Date, .*, Running Balance header"):
        parse_payoneer(REAL_ROWS.replace("Running Balance", ""))


def test_the_real_header_names_the_holder_currency_and_period() -> None:
    parsed = parse_payoneer(REAL_ROWS)
    assert (parsed.account_title, parsed.currency) == ("SYN HOLDER", "USD")
    assert (parsed.period_from, parsed.period_to) == (date(2024, 2, 1), date(2024, 2, 29))


SPLIT_HEADER = (
    REAL_ROWS.replace(
        "SYN HOLDER                                      Account USD balance\n", "SYN HOLDER\n"
    )
    .replace("0000000000\n", "0000000000\nAccount EUR balance\n")
    .replace(" USD", " EUR")
)


def test_a_header_whose_right_column_has_lines_of_its_own_reads() -> None:
    parsed = parse_payoneer(SPLIT_HEADER)
    assert (parsed.account_title, parsed.currency) == ("SYN HOLDER", "EUR")


def test_the_holder_is_the_first_line_whichever_line_the_currency_shares() -> None:
    moved = REAL_ROWS.replace(
        "SYN HOLDER                                      Account USD balance\nSYN ADDRESS  ",
        "SYN HOLDER\nSYN ADDRESS                                     Account USD balance  ",
    )
    assert parse_payoneer(moved).account_title == "SYN HOLDER"


def test_a_statement_without_its_header_says_so() -> None:
    with pytest.raises(StatementError, match=r"Account \.\.\. balance"):
        parse_payoneer(REAL_ROWS.replace("Account USD balance", ""))
