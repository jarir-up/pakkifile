"""ePRC and S-PRC certificates (ADR-0057). Files are read, never modified (R-29).

Layout source: a public e-PRC sample (Habib Metropolitan Bank, 2026-11-12): a certificate
number and date, the remitter's and beneficiary's details side by side, then a transaction
table of label and value pairs. An S-PRC is read as several such certificates in one file;
its own layout is not yet confirmed. Every figure is stored exactly as printed: the PKR
amount is never recomputed from the rate (R-20). The foreign amount and the rate may be
blank or "N/A" (owner, 2026-11-13).

A certificate proves the statement credit of the same PKR amount booked on its date of
realization or up to 3 days after it (ADR-0058).
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import Connection, Row, insert, select, update

from pakkifile.figures.money import parse_minor
from pakkifile.vault.ingest import ingest_once
from pakkifile.vault.schema import prc_certificate, statement_row
from pakkifile.vault.statements import StatementError, pdf_text, statement_lines

_NUMBER = re.compile(r"e-PRC No\.\s+(\S+)")
_DATED = re.compile(r"Date of e-PRC:\s+(\d{2}-[A-Z][a-z]{2}-\d{4})")
# The beneficiary's label is the last "Name" on the line: a remitter may have "Name" in it.
_NAMES = re.compile(r"^Name\s+(?P<remitter>.+)\s+Name\s+(?P<beneficiary>.+?)\s*$")
_LABELS = {
    "realized": "Date of Realization of Proceeds",
    "foreign": "Amount of Remittance (in FCY)*",
    "rate": "Rate of Conversion*",
    "pkr": "Amount of Remittance (in PKR)",
    "purpose": "Purpose of Remittance",
}
_FOREIGN = re.compile(r"([A-Z]{3}) (-?[\d,]+(?:\.\d{2})?)")
_NONE = ("", "N/A")  # what banks print when the remitting bank abroad holds the figure
MATCH_WITHIN = timedelta(days=3)  # after the date of realization (ADR-0058)
_ANY_LABEL = re.compile(r"^\S.*?\s{2,}\S|^(Transaction|Purpose Code|Note|i+\.|\*)")


@dataclass(frozen=True)
class Certificate:
    number: str
    issued: date
    remitter: str
    realized: date
    foreign_minor: int | None  # None when the certificate leaves it blank or "N/A"
    foreign_currency: str | None
    rate: Decimal | None
    pkr_minor: int
    purpose: str


def _day(text: str) -> date:
    return datetime.strptime(text, "%d-%b-%Y").date()


def _value(lines: list[str], label: str) -> str:
    """The value beside `label`, with any lines it wraps onto, up to a blank or labelled line."""
    for index, line in enumerate(lines):
        if line.strip().startswith(label):
            parts = [line.strip().removeprefix(label).strip()]
            for more in lines[index + 1 :]:
                if not more.strip() or _ANY_LABEL.match(more.strip()):
                    break
                parts.append(more.strip())
            return " ".join(parts)
    raise StatementError(f"not an e-PRC: no {label!r}")


def _certificate(lines: list[str]) -> Certificate:
    text = "\n".join(lines)
    number, dated = _NUMBER.search(text), _DATED.search(text)
    names = next((m for line in lines if (m := _NAMES.match(line.strip()))), None)
    if number is None or dated is None or names is None:
        raise StatementError("not an e-PRC: no certificate number, date or remitter")
    foreign_text = _value(lines, _LABELS["foreign"])
    foreign = _FOREIGN.fullmatch(foreign_text)
    if foreign is None and foreign_text not in _NONE:
        raise StatementError(f"unreadable foreign amount: {foreign_text!r}")
    rate_text = _value(lines, _LABELS["rate"])
    try:
        return Certificate(
            number=number[1],
            issued=_day(dated[1]),
            remitter=names["remitter"],
            realized=_day(_value(lines, _LABELS["realized"])),
            foreign_minor=parse_minor(foreign[2]) if foreign else None,
            foreign_currency=foreign[1] if foreign else None,
            rate=None if rate_text in _NONE else Decimal(rate_text),
            pkr_minor=parse_minor(_value(lines, _LABELS["pkr"])),
            purpose=_value(lines, _LABELS["purpose"]),
        )
    except (ValueError, InvalidOperation) as error:
        raise StatementError(f"unreadable certificate {number[1]}: {error}") from error


def parse_prc(text: str) -> tuple[Certificate, ...]:
    """Every certificate in the text: one for an e-PRC, several for an S-PRC."""
    lines = statement_lines(text)
    starts = [i for i, line in enumerate(lines) if _NUMBER.search(line)]
    if not starts:
        raise StatementError("not an e-PRC: no certificate number")
    starts[0] = 0  # the bank's name and title sit above the first number
    ends = [*starts[1:], len(lines)]
    return tuple(_certificate(lines[a:b]) for a, b in zip(starts, ends, strict=True))


def ingest_prc_pdf(
    conn: Connection, person_id: int, path: Path, password: str | None = None
) -> int:
    """Store every certificate in a file for one person, all or nothing (ADR-0057).

    Certificates are stored unmatched; `match_certificates` links them once both the
    certificates and the statements are in the vault, whichever arrives first.
    """

    def store(certificates: tuple[Certificate, ...], item_id: int) -> None:
        conn.execute(
            insert(prc_certificate),
            [
                {
                    "person_id": person_id,
                    "evidence_item_id": item_id,
                    "certificate_no": c.number,
                    "issued": c.issued,
                    "remitter": c.remitter,
                    "realized": c.realized,
                    "foreign_minor": c.foreign_minor,
                    "foreign_currency": c.foreign_currency,
                    "rate": c.rate,
                    "pkr_minor": c.pkr_minor,
                    "purpose": c.purpose,
                }
                for c in certificates
            ],
        )

    return ingest_once(conn, person_id, path, lambda: parse_prc(pdf_text(path, password)), store)


def match_certificates(conn: Connection, person_id: int) -> int:
    """Link each unmatched certificate to the credit it proves; returns how many were linked.

    The credit has exactly the certificate's PKR amount and is booked from its date of
    realization to 3 days after. The nearest date wins, and a credit proves one certificate.
    """
    linked = 0
    taken = select(prc_certificate.c.statement_row_id).where(
        prc_certificate.c.person_id == person_id,
        prc_certificate.c.statement_row_id.is_not(None),
    )
    for cert in unmatched_certificates(conn, person_id):
        credit = conn.scalar(
            select(statement_row.c.id)
            .where(
                statement_row.c.person_id == person_id,
                statement_row.c.currency == "PKR",  # a certificate proves rupees paid out
                statement_row.c.amount_minor == cert.pkr_minor,
                statement_row.c.date.between(cert.realized, cert.realized + MATCH_WITHIN),
                statement_row.c.id.not_in(taken),
            )
            .order_by(statement_row.c.date, statement_row.c.id)
            .limit(1)
        )
        if credit is not None:
            conn.execute(
                update(prc_certificate)
                .where(prc_certificate.c.id == cert.id)
                .values(statement_row_id=credit)
            )
            linked += 1
    return linked


def unmatched_certificates(
    conn: Connection, person_id: int
) -> list[Row[tuple[int, str, int, date]]]:
    """This person's certificates no statement credit proves yet (ADR-0057), oldest first."""
    return list(
        conn.execute(
            select(
                prc_certificate.c.id,
                prc_certificate.c.certificate_no,
                prc_certificate.c.pkr_minor,
                prc_certificate.c.realized,
            )
            .where(
                prc_certificate.c.person_id == person_id,
                prc_certificate.c.statement_row_id.is_(None),
            )
            .order_by(prc_certificate.c.realized, prc_certificate.c.id)
        )
    )
