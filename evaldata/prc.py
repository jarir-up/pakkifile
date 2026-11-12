"""Synthetic e-PRC and S-PRC certificates in the real layout (ADR-0057).

Layout source: a public e-PRC sample (2026-11-12). A certificate is issued for each
remittance whose memo names a PRC; a SWIFT payment without one gets none (seed M1). An S-PRC
is written as every certificate in one file, one per page; its own layout is not yet seen.
"""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from evaldata.pdf import amount_text, write_pdf
from evaldata.persona import Persona, Transaction, transactions
from pakkifile.figures.money import ROUNDING

BANK = "SYN BANK LTD"  # not a real bank's name: this file imitates no one
PURPOSE = "Freelance of computer and information services"
ISSUED_AFTER = timedelta(days=30)  # banks issue certificates well after the money arrives


def _date(day: date) -> str:
    return day.strftime("%d-%b-%Y")


def prc_remittances(persona: Persona) -> list[Transaction]:
    """The remittances a bank certifies: those whose memo names a PRC."""
    return [
        t
        for t in transactions(persona)
        if t.row_class == "remittance_in" and t.description.endswith("PRC")
    ]


def _page(persona: Persona, t: Transaction, number: int) -> list[str]:
    usd_minor = int((Decimal(t.amount_minor) / persona.usd_pkr).quantize(0, ROUNDING))
    remitter = t.description.removeprefix("HOME REMITTANCE ").removesuffix(" PRC")
    holder = persona.accounts["meezan"].holder
    pairs = (
        ("Date of Realization of Proceeds", _date(t.date)),
        ("Amount of Remittance (in FCY)*", f"USD {amount_text(usd_minor)}"),
        ("Rate of Conversion*", f"{persona.usd_pkr:.2f}"),
        ("Amount of Remittance (in PKR)", amount_text(t.amount_minor)),
        ("Purpose of Remittance", PURPOSE),
        ("Purpose Code (as per ITRS)", "9186"),
        ("Transaction Reference No.", f"0000-{number:010d}"),
    )
    return [
        BANK,
        " " * 20 + "Electronic Proceeds Realization Certificate (e-PRC)",
        "SYNTHETIC CERTIFICATE - NOT A BANK DOCUMENT",
        "",
        " " * 46 + "e-PRC No.".ljust(19) + f"SYN-{t.date.year}-{number:06d}",
        " " * 46 + "Date of e-PRC:".ljust(19) + _date(t.date + ISSUED_AFTER),
        "",
        "Remitter's Detail".ljust(46) + "Beneficiary's Detail",
        "",
        "Name".ljust(20) + remitter + " Name".ljust(21) + holder,
        "",
        "Name of Country".ljust(20) + "United States",
        "",
        "Transaction Detail",
        *(label.ljust(45) + value for label, value in pairs),
    ]


def write_prc(persona: Persona, out_dir: Path) -> list[Path]:
    """One e-PRC file per remittance, in booking order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    return [
        write_pdf([_page(persona, t, n)], out_dir / f"{persona.id}-eprc-{n:03d}-synthetic.pdf")
        for n, t in enumerate(prc_remittances(persona), start=1)
    ]


def write_sprc(persona: Persona, out_dir: Path) -> Path:
    """Every certificate in one S-PRC file, a page each."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = [_page(persona, t, n) for n, t in enumerate(prc_remittances(persona), start=1)]
    return write_pdf(pages, out_dir / f"{persona.id}-sprc-synthetic.pdf")
