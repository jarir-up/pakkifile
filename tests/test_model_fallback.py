import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Connection, select

from evaldata.meezan import write_meezan_statement
from evaldata.persona import load_personas
from pakkifile.llm.classify_row import ClassifyModel, classify_memo
from pakkifile.llm.ollama import ModelError
from pakkifile.vault import statements
from pakkifile.vault.fallback import classify_pending
from pakkifile.vault.ingest import add_person
from pakkifile.vault.meezan import ingest_meezan_pdf
from pakkifile.vault.review import REVIEW_BELOW, awaiting_review
from pakkifile.vault.schema import statement_row
from pakkifile.vault.statements import pdf_text
from tests.helpers import FakeOllama

AMBIGUOUS = "IBFT SYN PERSON NAWAZ 0001"


@pytest.fixture
def ollama() -> Iterator[FakeOllama]:
    fake = FakeOllama(json.dumps({"row_class": "spending", "confidence": 0.95}))
    yield fake
    fake.server.shutdown()


def _prompt(fake: FakeOllama) -> str:
    return str(fake.requests[-1]["messages"][-1]["content"])


def test_the_model_sees_the_memo_redacted_and_never_the_amount(ollama: FakeOllama) -> None:
    result = classify_memo("Raast P2P to SYN NAWAZ 03001234567", "debit", ollama.model)
    prompt = _prompt(ollama)
    assert "<memo>Raast P2P to [NAME] [PHONE]</memo>" in prompt
    assert "NAWAZ" not in prompt and "03001234567" not in prompt
    assert "debit" in prompt
    assert (result.row_class, result.confidence) == ("spending", 0.95)


def test_output_is_constrained_to_the_classes_or_unclassified(ollama: FakeOllama) -> None:
    ollama.content = json.dumps({"row_class": "unclassified", "confidence": 0.4})
    assert classify_memo("SYN THING", "credit", ollama.model).row_class is None
    choices = ollama.requests[-1]["format"]["properties"]["row_class"]["enum"]
    assert {"spending", "remittance_in", "unclassified"} <= set(choices)


@pytest.mark.parametrize(
    "content",
    [
        json.dumps({"row_class": "lottery", "confidence": 0.9}),
        json.dumps({"row_class": "fee", "confidence": 1.5}),
        "not json",
    ],
)
def test_output_outside_the_schema_is_an_error(ollama: FakeOllama, content: str) -> None:
    ollama.content = content
    with pytest.raises(ModelError):
        classify_memo("SYN THING", "credit", ollama.model)


def test_the_classification_model_defaults_to_thinking_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAKKIFILE_CLASSIFY_MODEL", "qwen3:8b")
    monkeypatch.delenv("PAKKIFILE_CLASSIFY_THINK", raising=False)
    assert (ClassifyModel.from_env().name, ClassifyModel.from_env().think) == ("qwen3:8b", False)


def _ingest_with_one_ambiguous_row(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> int:
    path = write_meezan_statement(load_personas()["syn-dev-payoneer"], tmp_path)
    text = pdf_text(path).replace("IBFT kiraya makaan", AMBIGUOUS, 1)
    monkeypatch.setattr(statements, "pdf_text", lambda *_: text)
    person = add_person(db, "applicant")
    ingest_meezan_pdf(db, person, path)
    return person


def _row(db: Connection, description: str) -> tuple[object, ...]:
    row = db.execute(
        select(
            statement_row.c.row_class,
            statement_row.c.class_source,
            statement_row.c.class_confidence,
            statement_row.c.needs_review,
        ).where(statement_row.c.description == description)
    ).first()
    assert row is not None
    return tuple(row)


def test_only_rows_the_rules_left_reach_the_model(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ollama: FakeOllama
) -> None:
    person = _ingest_with_one_ambiguous_row(db, tmp_path, monkeypatch)
    assert classify_pending(db, person, ollama.model) == 1
    assert len(ollama.requests) == 1
    assert _row(db, AMBIGUOUS) == ("spending", "model", 0.95, True)
    assert _row(db, "ATM CASH WITHDRAWAL")[1] == "rule"
    assert classify_pending(db, person, ollama.model) == 0  # never sent twice


@pytest.mark.parametrize(
    ("reply", "first"),
    [
        ({"row_class": "spending", "confidence": REVIEW_BELOW - 0.01}, True),
        ({"row_class": "unclassified", "confidence": 0.9}, True),
        ({"row_class": "spending", "confidence": REVIEW_BELOW}, False),
    ],
)
def test_every_row_waits_for_review_with_the_uncertain_ones_first(
    db: Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ollama: FakeOllama,
    reply: dict[str, object],
    first: bool,
) -> None:
    person = _ingest_with_one_ambiguous_row(db, tmp_path, monkeypatch)
    ollama.content = json.dumps(reply)
    classify_pending(db, person, ollama.model)
    queue = awaiting_review(db, person)
    needs_review = [_row(db, row.description)[-1] for row in queue]  # last column selected
    assert all(needs_review)
    assert (queue[0].description == AMBIGUOUS) is first
