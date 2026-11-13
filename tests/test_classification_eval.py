import json
from collections.abc import Iterator

import pytest

from eval.classification import Item, items, score
from evaldata.persona import load_personas
from pakkifile.llm.classify_row import ModelClass
from tests.helpers import FakeOllama


def test_every_distinct_persona_memo_is_an_item_with_its_label() -> None:
    found = items(load_personas().values())
    assert len(found) == len({(i.memo, i.direction) for i in found}) > 20
    assert {i.label for i in found} >= {"remittance_in", "spending", "client_payment"}


def test_score_counts_right_unclassified_and_confidently_wrong() -> None:
    cases = [
        (Item("a", "credit", "fee"), ModelClass("fee", 0.9)),
        (Item("b", "debit", "spending"), ModelClass(None, 0.3)),
        (Item("c", "debit", "tax"), ModelClass("fee", 0.95)),  # wrong and sure: the worst
        (Item("d", "debit", "tax"), ModelClass("fee", 0.5)),  # wrong but unsure: goes to review
    ]
    result = score(cases)
    assert (result.right, result.unclassified, result.confident_wrong) == (1, 1, 1)
    assert result.total == 4
    assert [line.split(" (")[0] for line in result.wrong] == ["c", "d"]
    assert result.right_by_class == {"fee": (1, 1), "spending": (0, 1), "tax": (0, 2)}


@pytest.fixture
def ollama() -> Iterator[FakeOllama]:
    fake = FakeOllama(json.dumps({"row_class": "spending", "confidence": 0.9}))
    yield fake
    fake.server.shutdown()


def test_the_evaluation_asks_the_model_for_every_item(ollama: FakeOllama) -> None:
    from eval.classification import evaluate

    found = items(load_personas().values())
    result = evaluate(found, ollama.model)
    assert len(ollama.requests) == len(found) == result.total
