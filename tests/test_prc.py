from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Connection, select

from evaldata.meezan import write_meezan_statement
from evaldata.persona import Persona, load_personas, transactions
from evaldata.prc import prc_remittances, write_prc, write_sprc
from pakkifile.vault.ingest import add_person
from pakkifile.vault.meezan import ingest_meezan_pdf
from pakkifile.vault.prc import (
    ingest_prc_pdf,
    match_certificates,
    parse_prc,
    unmatched_certificates,
)
from pakkifile.vault.schema import prc_certificate, statement_row
from pakkifile.vault.statements import StatementError, pdf_text

ALL = load_personas()

# The real e-PRC layout (a public bank sample, 2026-11-12), every value replaced.
REAL = """SYN BANK LTD
                                        Electronic Proceeds Realization Certificate (e-PRC)


                                                                            e-PRC No.                  SYN-2024-000001

                                                                            Date of e-PRC:             26-Aug-2024

Remitter's Detail                                                           Beneficiary's Detail


Name                                SYN CLIENT DEVELOPMENT APS Name                            SYN HOLDER


Name of Country                     Denmark

Country Code (as per ITRS)          420

Transaction Detail
Date of Realization of Proceeds              29-May-2024

Amount of Remittance (in FCY)*              EUR 1,000.00

Rate of Conversion*                          300.25

Amount of Remittance (in PKR)                300,250.70

Purpose of Remittance                        Freelance of computer and information services

Purpose Code (as per ITRS)                   9186

Transaction Reference No.                    0000-0000000000
"""


def test_the_real_layout_reads_every_field_as_printed() -> None:
    (cert,) = parse_prc(REAL)
    assert (cert.number, cert.issued) == ("SYN-2024-000001", date(2024, 8, 26))
    assert cert.remitter == "SYN CLIENT DEVELOPMENT APS"
    assert (cert.foreign_minor, cert.foreign_currency) == (100_000, "EUR")
    assert cert.rate == Decimal("300.25")
    # As printed, even where it isn't the foreign amount times the rate: never recomputed.
    assert cert.pkr_minor == 30_025_070
    assert cert.purpose == "Freelance of computer and information services"


def test_a_rate_applied_abroad_reads_as_none() -> None:
    (cert,) = parse_prc(REAL.replace("300.25\n", "N/A\n"))
    assert cert.rate is None


def test_a_remitter_named_with_the_word_name_keeps_it() -> None:
    (cert,) = parse_prc(REAL.replace("SYN CLIENT DEVELOPMENT APS", "SYN Name STUDIO"))
    assert cert.remitter == "SYN Name STUDIO"


def test_a_purpose_that_wraps_is_read_whole() -> None:
    wrapped = REAL.replace(
        "Freelance of computer and information services\n",
        "Freelance of computer and\n                                             information services\n",
    )
    (cert,) = parse_prc(wrapped)
    assert cert.purpose == "Freelance of computer and information services"


def test_a_whole_number_foreign_amount_reads() -> None:
    (cert,) = parse_prc(REAL.replace("EUR 1,000.00", "EUR 1,000"))
    assert cert.foreign_minor == 100_000


@pytest.mark.parametrize(
    ("printed", "replacement"),
    [("EUR 1,000.00", "1,000.00 EUR"), ("300.25\n", "about 300\n"), ("26-Aug-2024", "26-08-2024")],
)
def test_an_unreadable_field_stops_the_parse(printed: str, replacement: str) -> None:
    with pytest.raises(StatementError):
        parse_prc(REAL.replace(printed, replacement))


def test_text_that_is_not_a_certificate_is_refused() -> None:
    with pytest.raises(StatementError, match="not an e-PRC"):
        parse_prc("A bank statement")


def _remittances(persona: Persona) -> list[int]:
    return [t.amount_minor for t in prc_remittances(persona)]


@pytest.mark.parametrize("persona", ALL.values(), ids=lambda p: p.id)
def test_each_certificate_the_generator_writes_reads_back(persona: Persona, tmp_path: Path) -> None:
    paths = write_prc(persona, tmp_path)
    certs = [cert for path in paths for cert in parse_prc(pdf_text(path))]
    assert [c.pkr_minor for c in certs] == _remittances(persona)
    assert {c.foreign_currency for c in certs} == {"USD"}


def test_a_swift_payment_without_a_prc_gets_no_certificate(tmp_path: Path) -> None:
    designer = ALL["syn-designer-direct"]
    certs = [c for p in write_prc(designer, tmp_path) for c in parse_prc(pdf_text(p))]
    remittances = [t for t in transactions(designer) if t.row_class == "remittance_in"]
    swift = [t for t in remittances if t.description.startswith("INWARD SWIFT")]
    assert swift  # the seeded M1: one SWIFT payment with no PRC
    assert len(certs) == len(remittances) - len(swift)


def test_an_sprc_holds_every_certificate_in_one_file(tmp_path: Path) -> None:
    persona = ALL["syn-dev-payoneer"]
    certs = parse_prc(pdf_text(write_sprc(persona, tmp_path)))
    assert [c.pkr_minor for c in certs] == _remittances(persona)
    assert len({c.number for c in certs}) == len(certs)


def test_ingest_stores_each_certificate_once_and_unmatched(db: Connection, tmp_path: Path) -> None:
    persona = ALL["syn-dev-payoneer"]
    person = add_person(db, "applicant")
    path = write_sprc(persona, tmp_path)
    item = ingest_prc_pdf(db, person, path)
    assert ingest_prc_pdf(db, person, path) == item  # the same file is stored once
    stored = db.execute(
        select(prc_certificate.c.pkr_minor, prc_certificate.c.statement_row_id).where(
            prc_certificate.c.person_id == person
        )
    ).all()
    assert [s.pkr_minor for s in stored] == _remittances(persona)
    assert {s.statement_row_id for s in stored} == {None}  # no statement in the vault yet


@pytest.mark.parametrize("printed", ["N/A", ""])
def test_a_foreign_amount_left_blank_or_na_is_stored_as_none(printed: str) -> None:
    (cert,) = parse_prc(REAL.replace("EUR 1,000.00", printed))
    assert (cert.foreign_minor, cert.foreign_currency) == (None, None)
    assert cert.pkr_minor == 30_025_070


def test_the_date_of_realization_is_read() -> None:
    (cert,) = parse_prc(REAL)
    assert cert.realized == date(2024, 5, 29)


def _ingest_dev(db: Connection, tmp_path: Path) -> int:
    person = add_person(db, "applicant")
    ingest_meezan_pdf(db, person, write_meezan_statement(ALL["syn-dev-payoneer"], tmp_path))
    ingest_prc_pdf(db, person, write_sprc(ALL["syn-dev-payoneer"], tmp_path))
    return person


def test_each_certificate_is_linked_to_its_credit(db: Connection, tmp_path: Path) -> None:
    person = _ingest_dev(db, tmp_path)
    assert match_certificates(db, person) == len(_remittances(ALL["syn-dev-payoneer"]))
    linked = db.execute(
        select(prc_certificate.c.pkr_minor, statement_row.c.amount_minor, statement_row.c.date)
        .join(statement_row, statement_row.c.id == prc_certificate.c.statement_row_id)
        .where(prc_certificate.c.person_id == person)
    ).all()
    assert all(pkr == amount for pkr, amount, _ in linked)
    assert unmatched_certificates(db, person) == []
    assert match_certificates(db, person) == 0  # nothing left to link


def test_a_credit_booked_outside_the_window_leaves_the_certificate_unmatched(
    db: Connection, tmp_path: Path
) -> None:
    person = _ingest_dev(db, tmp_path)
    first = db.execute(
        select(prc_certificate.c.id, prc_certificate.c.realized)
        .where(prc_certificate.c.person_id == person)
        .order_by(prc_certificate.c.realized)
    ).first()
    assert first is not None
    db.execute(
        prc_certificate.update()
        .where(prc_certificate.c.id == first.id)
        .values(realized=first.realized - timedelta(days=4))  # the credit lands 4 days later
    )
    match_certificates(db, person)
    assert [c.id for c in unmatched_certificates(db, person)] == [first.id]


def test_one_credit_proves_only_one_certificate(db: Connection, tmp_path: Path) -> None:
    person = _ingest_dev(db, tmp_path)
    cert = db.execute(select(prc_certificate).where(prc_certificate.c.person_id == person)).first()
    assert cert is not None
    copy = {k: v for k, v in cert._asdict().items() if k != "id"}
    db.execute(prc_certificate.insert().values({**copy, "certificate_no": "SYN-COPY"}))
    match_certificates(db, person)
    assert [c.certificate_no for c in unmatched_certificates(db, person)] == ["SYN-COPY"]


@pytest.mark.parametrize("printed", ["N/A", ""])
def test_a_rate_left_blank_or_na_is_stored_as_none(printed: str) -> None:
    (cert,) = parse_prc(REAL.replace("300.25\n", f"{printed}\n"))
    assert cert.rate is None


def _only_certificate(db: Connection, tmp_path: Path) -> tuple[int, int, int]:
    """A person with one certificate and no statement: (person, certificate id, PKR amount)."""
    person = add_person(db, "applicant")
    ingest_prc_pdf(db, person, write_prc(ALL["syn-dev-payoneer"], tmp_path)[0])
    (cert,) = unmatched_certificates(db, person)
    return person, cert.id, cert.pkr_minor


def _credit(db: Connection, person: int, amount: int, day: date, currency: str = "PKR") -> int:
    item = db.scalar(
        select(prc_certificate.c.evidence_item_id).where(prc_certificate.c.person_id == person)
    )
    return int(
        db.execute(
            statement_row.insert()
            .values(
                person_id=person,
                evidence_item_id=item,
                row_no=1,
                date=day,
                description="SYN CREDIT",
                amount_minor=amount,
                currency=currency,
                needs_review=True,
            )
            .returning(statement_row.c.id)
        ).scalar_one()
    )


def test_a_credit_in_another_currency_never_proves_a_certificate(
    db: Connection, tmp_path: Path
) -> None:
    person, cert, pkr = _only_certificate(db, tmp_path)
    realized = db.scalar(select(prc_certificate.c.realized).where(prc_certificate.c.id == cert))
    assert realized is not None
    _credit(db, person, pkr, realized, currency="USD")
    assert match_certificates(db, person) == 0


def test_the_credit_nearest_the_date_of_realization_wins(db: Connection, tmp_path: Path) -> None:
    person, cert, pkr = _only_certificate(db, tmp_path)
    realized = db.scalar(select(prc_certificate.c.realized).where(prc_certificate.c.id == cert))
    assert realized is not None
    _credit(db, person, pkr, realized + timedelta(days=3))
    nearest = _credit(db, person, pkr, realized + timedelta(days=1))
    match_certificates(db, person)
    linked = db.scalar(
        select(prc_certificate.c.statement_row_id).where(prc_certificate.c.id == cert)
    )
    assert linked == nearest
