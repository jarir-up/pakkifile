"""Put evidence files into the vault: statements and certificates, told apart by their text.

uv run python -m pakkifile.vault FILE... [--person ID]
"""

import argparse
import getpass
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import Connection, select

from pakkifile.llm.classify_row import ClassifyModel
from pakkifile.llm.ollama import LocalModel, ModelError
from pakkifile.vault.db import open_vault
from pakkifile.vault.fallback import classify_pending
from pakkifile.vault.ingest import add_person
from pakkifile.vault.meezan import ingest_meezan_pdf
from pakkifile.vault.payoneer import ingest_payoneer_pdf
from pakkifile.vault.prc import ingest_prc_pdf, match_certificates, unmatched_certificates
from pakkifile.vault.schema import person
from pakkifile.vault.statements import StatementError, read_pdf

Kind = Literal["meezan", "payoneer", "prc"]
_INGEST = {"meezan": ingest_meezan_pdf, "payoneer": ingest_payoneer_pdf, "prc": ingest_prc_pdf}


def kind_of(text: str) -> Kind:
    if "Booking Date" in text and "Available Balance" in text:
        return "meezan"
    if "Running Balance" in text and "Issuing Date" in text:
        return "payoneer"
    if "e-PRC No." in text:
        return "prc"
    raise StatementError("not a Meezan or Payoneer statement or an e-PRC")


@dataclass(frozen=True)
class Ingested:
    files: list[tuple[str, Kind]]  # each file's name and what it was read as
    classified: int | None  # rows the model classified; None when no model ran
    unmatched: list[str]  # certificates no statement credit proves yet (ADR-0057)
    model_error: str | None = None  # why the model couldn't run; its rows wait for review


def ingest_files(
    conn: Connection,
    person_id: int,
    paths: Sequence[Path],
    password: Callable[[Path], str | None],
    model: LocalModel | None,
) -> Ingested:
    """Store each file, then send the rows the rules left to the model, if there is one."""
    if conn.scalar(select(person.c.id).where(person.c.id == person_id)) is None:
        raise StatementError(f"no person {person_id} in the vault")
    files = []
    for path in paths:
        text, given = read_pdf(path, password)
        kind = kind_of(text)
        _INGEST[kind](conn, person_id, path, given)
        files.append((path.name, kind))
    match_certificates(conn, person_id)  # certificates and statements may arrive in any order
    unmatched = [c.certificate_no for c in unmatched_certificates(conn, person_id)]
    if model is None:
        return Ingested(files, None, unmatched)
    try:
        return Ingested(files, classify_pending(conn, person_id, model), unmatched)
    except ModelError as error:
        return Ingested(files, None, unmatched, str(error))


def _report(done: Ingested, person_id: int) -> str:
    lines = [f"{name}: {kind}" for name, kind in done.files]
    if done.classified is not None:
        lines.append(f"model: {done.classified} rows classified")
    if done.unmatched:
        lines.append(f"certificates with no matching credit: {', '.join(done.unmatched)}")
    if done.model_error:
        lines.append(f"model unavailable, rows wait for review: {done.model_error}")
    lines.append(f"review: uv run python -m pakkifile.web.app --person {person_id}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--person", type=int)
    args = parser.parse_args()
    model = ClassifyModel.from_env() if os.environ.get("PAKKIFILE_CLASSIFY_MODEL") else None
    try:
        with open_vault().begin() as conn:  # one run: every file is stored, or none is
            person_id = add_person(conn, "applicant") if args.person is None else args.person
            done = ingest_files(
                conn,
                person_id,
                args.files,
                lambda path: getpass.getpass(f"Password for {path.name}: "),
                model,
            )
    except StatementError as error:
        sys.exit(f"Nothing stored: {error}")
    print(_report(done, person_id))


if __name__ == "__main__":
    main()
