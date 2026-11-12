import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from eval import memo_lines
from eval.memo_lines import distinct_memos, spread
from pakkifile.vault.statements import Statement, StatementRow


def _row(description: str, credit: int = 0, debit: int = 0) -> StatementRow:
    return StatementRow(1, date(2024, 7, 2), description, credit, debit, 0)


def test_memos_are_masked_and_listed_once_per_direction() -> None:
    rows = (
        _row("Cash Deposit 1289318", credit=100),
        _row("Cash Deposit 5550001", credit=200),
        _row("IBFT ALI 4417", debit=300),
        _row("IBFT ALI 4417", credit=300),
    )
    assert distinct_memos(rows) == [
        ("credit", "Cash Deposit 0000000"),
        ("debit", "IBFT ALI 0000"),
        ("credit", "IBFT ALI 0000"),
    ]


def test_a_long_statement_is_sampled_across_its_whole_length() -> None:
    items: list[memo_lines.Memo] = [("credit", str(n)) for n in range(90)]
    picked = spread(items, limit=30)
    assert picked == items[::3]  # every third: 90 memos, 30 kept


def test_the_label_file_reads_back_every_memo_exactly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memo = """IBFT O'BRIEN "RENT" back\\slash"""
    monkeypatch.setattr(memo_lines, "OUT", tmp_path / "memos.yaml")
    monkeypatch.setattr(memo_lines, "read_pdf", lambda *_: ("", None))
    monkeypatch.setattr(
        memo_lines,
        "parse_meezan",
        lambda _: Statement(
            "", "", None, "PKR", date(2024, 7, 1), date(2024, 7, 2), 0, 0, (_row(memo, debit=1),)
        ),
    )
    monkeypatch.setattr(sys, "argv", ["memo_lines", "statement.pdf"])
    memo_lines.main()
    (entry,) = yaml.safe_load((tmp_path / "memos.yaml").read_text())
    assert entry == {"direction": "debit", "memo": memo, "class": None}


def test_an_unreadable_statement_stops_with_its_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(memo_lines, "OUT", tmp_path / "memos.yaml")
    monkeypatch.setattr(memo_lines, "read_pdf", lambda *_: ("not a statement", None))
    monkeypatch.setattr(sys, "argv", ["memo_lines", "statement.pdf"])
    with pytest.raises(SystemExit, match=r"Can't read statement\.pdf: not a Meezan"):
        memo_lines.main()
    assert not (tmp_path / "memos.yaml").exists()
