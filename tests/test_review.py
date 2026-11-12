import socket
import threading
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI
from sqlalchemy import Connection, select, update

from evaldata.meezan import write_meezan_statement
from evaldata.persona import load_personas
from pakkifile.vault import statements
from pakkifile.vault.ingest import add_person
from pakkifile.vault.meezan import ingest_meezan_pdf
from pakkifile.vault.review import ReviewError, awaiting_review, decide
from pakkifile.vault.schema import row_correction, statement_row
from pakkifile.vault.statements import pdf_text
from pakkifile.web.app import HOST, create_app

AMBIGUOUS = "IBFT SYN PERSON NAWAZ 0001"
NOW = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)


@pytest.fixture
def person(db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    """One applicant with one row the rules couldn't place, proposed as spending by the model."""
    path = write_meezan_statement(load_personas()["syn-dev-payoneer"], tmp_path)
    text = pdf_text(path).replace("IBFT kiraya makaan", AMBIGUOUS, 1)
    monkeypatch.setattr(statements, "pdf_text", lambda *_: text)
    person = add_person(db, "applicant")
    ingest_meezan_pdf(db, person, path)
    db.execute(
        update(statement_row)
        .where(statement_row.c.description == AMBIGUOUS)
        .values(row_class="spending", class_source="model", class_confidence=0.6)
    )
    return person


def _row_id(db: Connection) -> int:
    query = select(statement_row.c.id).where(statement_row.c.description == AMBIGUOUS)
    return int(db.execute(query).scalar_one())


def test_only_this_persons_rows_awaiting_review_are_listed(db: Connection, person: int) -> None:
    row, *rest = awaiting_review(db, person)  # the uncertain one first, then every other row
    assert (row.description, row.proposed, row.source) == (AMBIGUOUS, "spending", "model")
    assert rest and {r.source for r in rest} == {"rule"}
    assert awaiting_review(db, add_person(db, "applicant")) == []


def test_a_decision_is_stored_as_evaluation_data_and_leaves_the_queue(
    db: Connection, person: int
) -> None:
    decide(db, person, _row_id(db), "sponsor_transfer", NOW)
    correction = db.execute(select(row_correction)).one()
    assert (correction.proposed_class, correction.proposed_source) == ("spending", "model")
    assert (correction.chosen_class, correction.decided_at) == ("sponsor_transfer", NOW)
    stored = db.execute(select(statement_row).where(statement_row.c.id == _row_id(db))).one()
    assert (stored.row_class, stored.class_source, stored.needs_review) == (
        "sponsor_transfer",
        "applicant",
        False,
    )
    assert AMBIGUOUS not in [r.description for r in awaiting_review(db, person)]


def test_another_persons_row_cannot_be_decided(db: Connection, person: int) -> None:
    with pytest.raises(ReviewError):
        decide(db, add_person(db, "applicant"), _row_id(db), "fee", NOW)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


class LocalApp:
    """The app served by uvicorn on a free local port, as the applicant runs it."""

    def __init__(self, app: FastAPI) -> None:
        with socket.socket() as probe:
            probe.bind((HOST, 0))
            port = probe.getsockname()[1]
        self.url = f"http://{HOST}:{port}"
        self.server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=port, log_level="error"))
        threading.Thread(target=self.server.run, daemon=True).start()
        while not self.server.started:
            time.sleep(0.01)

    def get(self) -> str:
        with urllib.request.urlopen(self.url) as response:
            return str(response.read().decode())

    def status(self, headers: dict[str, str]) -> int:
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url, headers=headers)) as r:
                return int(r.status)
        except urllib.error.HTTPError as error:
            return error.code

    def post(self, form: str) -> int:
        """Posts as the app's own page does."""
        return self.post_from(form, self.url)

    def post_from(self, form: str, origin: str | None) -> int:
        """Posts with this Origin header, or with none."""
        headers = {"content-type": "application/x-www-form-urlencoded"}
        if origin is not None:
            headers["origin"] = origin
        request = urllib.request.Request(self.url, data=form.encode(), headers=headers)
        try:
            with urllib.request.build_opener(_NoRedirect).open(request) as response:
                return int(response.status)
        except urllib.error.HTTPError as error:  # the 303 back to the page
            return error.code


@pytest.fixture
def client(db: Connection, person: int) -> Iterator[LocalApp]:
    @contextmanager
    def connect() -> Iterator[Connection]:
        yield db

    served = LocalApp(create_app(connect, person, clock=lambda: NOW))
    yield served
    served.server.should_exit = True


def test_the_page_lists_the_row_with_its_proposed_class_chosen(client: LocalApp) -> None:
    page = client.get()
    assert AMBIGUOUS in page
    assert '<option value="spending" selected>' in page


def test_saving_stores_each_decision_and_the_row_leaves_the_page(
    client: LocalApp, db: Connection
) -> None:
    assert client.post(f"row-{_row_id(db)}=fee") == 303
    assert db.scalar(select(row_correction.c.chosen_class)) == "fee"
    assert AMBIGUOUS not in client.get()


def test_a_row_left_undecided_stays_in_the_queue(client: LocalApp, db: Connection) -> None:
    client.post(f"row-{_row_id(db)}=")
    assert db.scalar(select(row_correction.c.id)) is None
    assert AMBIGUOUS in client.get()


def test_a_stale_form_keeps_the_choices_still_waiting(client: LocalApp, db: Connection) -> None:
    row = _row_id(db)
    client.post(f"row-{row}=fee")
    assert client.post(f"row-{row}=tax&row-999999=fee&row-abc=fee&row-{row}x=fee") == 303
    assert db.scalars(select(row_correction.c.chosen_class)).all() == ["fee"]


@pytest.mark.parametrize("origin", ["http://evil.example", None])
def test_a_post_from_any_other_page_is_refused(
    client: LocalApp, db: Connection, origin: str | None
) -> None:
    assert client.post_from(f"row-{_row_id(db)}=fee", origin) == 403
    assert db.scalar(select(row_correction.c.id)) is None


def test_a_request_for_another_host_name_is_refused(client: LocalApp) -> None:
    assert client.status({"host": "evil.example"}) == 400


def test_the_app_serves_this_machine_only() -> None:
    assert HOST == "127.0.0.1"
