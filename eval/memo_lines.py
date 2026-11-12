"""List a real Meezan statement's distinct memos, every digit masked, for the owner to label.

The held-out memo set (ADR-0029) comes from the owner's own statement, not from the rules'
author. Output goes only to the git-ignored /vault/ folder; the owner replaces any names
before anything is copied into the repo.

    uv run python -m eval.memo_lines vault/statement.pdf

A password, if the file has one, is asked for and never stored. A statement the parser
can't read stops here with the reason, which is itself what the parser needs to learn.
"""

import getpass
import json
import re
import sys
from pathlib import Path
from typing import get_args

from pakkifile.vault.classify import Direction, RowClass
from pakkifile.vault.meezan import parse_meezan
from pakkifile.vault.statements import StatementError, StatementRow, pdf_text

OUT = Path(__file__).resolve().parents[1] / "vault" / "memos-to-label.yaml"
LIMIT = 30
CLASSES = " ".join((*get_args(RowClass), "none"))
Memo = tuple[Direction, str]


def distinct_memos(rows: tuple[StatementRow, ...]) -> list[Memo]:
    """Distinct (direction, memo) pairs in statement order, digits replaced with 0."""
    seen: dict[Memo, None] = {}
    for row in rows:
        direction: Direction = "credit" if row.credit_minor else "debit"
        seen.setdefault((direction, re.sub(r"\d", "0", row.description)), None)
    return list(seen)


def spread(items: list[Memo], limit: int = LIMIT) -> list[Memo]:
    """At most `limit` items, taken evenly across the statement, not just its first month."""
    if len(items) <= limit:
        return items
    return [items[i * len(items) // limit] for i in range(limit)]


def _read(path: Path) -> str:
    """The statement's text, asking for its password only if it has one."""
    try:
        return pdf_text(path)
    except StatementError as error:
        if "password" not in str(error):
            raise
        return pdf_text(path, getpass.getpass(f"Password for {path.name}: "))


def main() -> None:
    path = Path(sys.argv[1])
    try:
        memos = distinct_memos(parse_meezan(_read(path)).rows)
    except StatementError as error:
        sys.exit(f"Can't read {path.name}: {error}")
    picked = spread(memos)
    entries = "".join(
        f"- direction: {direction}\n  memo: {json.dumps(memo)}\n  class:\n"
        for direction, memo in picked
    )
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        "# Replace any names with made-up ones, then give each memo one class:\n"
        f"# {CLASSES}\n\n{entries}"
    )
    print(f"{len(picked)} of {len(memos)} distinct memos written to {OUT}")


if __name__ == "__main__":
    main()
