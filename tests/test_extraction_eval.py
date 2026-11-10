from decimal import Decimal

import pytest

from eval import extraction
from eval.extraction import LABELS, Label, evaluate, load_labels, passes, score
from pakkifile.llm.extract import ExtractionModel
from pakkifile.registry.model import ExtractedItem, RequirementType
from tests.helpers import ISLAMABAD, entry

BLOCKED = "Confirmation letter for the blocked account with an amount of 10,236 €"
SAMPLE = (
    Label(text="Admission letters", type=("mandatory",), must_contain=("admission letter",)),
    Label(text=BLOCKED, type=("mandatory",), must_contain=("blocked account", "10236")),
    Label(text="O-level sheet", type=("mandatory",), must_contain=("o-level",)),
    Label(
        text="A-level sheet",
        type=("conditional",),
        must_contain=("a-level",),
        condition_contains="applicable",
    ),
    Label(text="List of children", type=("mandatory",), must_contain=("children",)),
)


def _item(
    text: str, kind: RequirementType = "mandatory", condition: str | None = None
) -> ExtractedItem:
    return ExtractedItem(text=text, type=kind, condition=condition)


def _perfect() -> list[ExtractedItem]:
    return [
        _item("Admission letter(s)"),
        _item(BLOCKED),
        _item("Copies of the O-level exam degree"),
        _item("Copies of the A-level exam degree", "conditional", "if applicable"),
        _item("List of children"),
    ]


def test_perfect_extraction_scores_full_marks() -> None:
    result = score(_perfect(), SAMPLE)
    assert (result.precision, result.recall) == (Decimal(1), Decimal(1))
    assert (result.type_accuracy, result.condition_accuracy) == (Decimal(1), Decimal(1))
    assert passes(result)


@pytest.mark.parametrize("amount", ["10,263 €", "102,360 €", "1,023 €", "10,236.99 €"])
def test_changed_amount_is_not_correct(amount: str) -> None:
    items = _perfect()
    items[1] = _item(f"Confirmation letter for the blocked account with an amount of {amount}")
    result = score(items, SAMPLE)
    assert result.recall == Decimal("0.8")
    assert BLOCKED in result.missing


@pytest.mark.parametrize("amount", ["€ 10236", "10.236 €", "10,236 €", "10 236 €"])
def test_amount_formats_count_as_the_same_number(amount: str) -> None:
    items = _perfect()
    items[1] = _item(f"Blocked account of {amount}")
    assert score(items, SAMPLE).recall == Decimal(1)


def test_o_level_listed_twice_does_not_cover_a_level() -> None:
    items = _perfect()
    items[3] = _item("Copies of the O-level exam degree", "conditional", "x")
    assert "A-level sheet" in score(items, SAMPLE).missing


def test_changed_amount_lowers_numbers_exact() -> None:
    items = _perfect()
    items[1] = _item("Confirmation letter for the blocked account with an amount of 11,904 €")
    assert score(items, SAMPLE).numbers_exact == Decimal(0)
    assert score(_perfect(), SAMPLE).numbers_exact == Decimal(1)


def test_a_level_of_something_is_not_an_a_level() -> None:
    items = _perfect()
    items[3] = _item("Language skills at a level of B2", "conditional", "if applicable")
    assert "A-level sheet" in score(items, SAMPLE).missing


def test_level_spelled_with_a_space_counts() -> None:
    items = _perfect()
    items[2] = _item("Copies of the O level exam degree")
    assert score(items, SAMPLE).recall == Decimal(1)


def test_similar_wording_without_the_key_word_is_not_a_match() -> None:
    items = _perfect()
    items[4] = _item("List of friends")
    result = score(items, SAMPLE)
    assert "List of children" in result.missing
    assert "List of friends" in result.extra


def test_junk_items_lower_precision() -> None:
    result = score([*_perfect(), _item("Original"), _item("Copy / printout")], SAMPLE)
    assert result.precision == Decimal(5) / Decimal(7)
    assert result.extra == ("Original", "Copy / printout")
    assert not passes(result)


def test_item_listed_by_the_page_but_not_required_is_neither_missing_nor_junk() -> None:
    labels = (
        *SAMPLE,
        Label(text="Pension", type=("optional",), must_contain=("pension",), required=False),
    )
    assert score(_perfect(), labels).recall == Decimal(1)
    result = score([*_perfect(), _item("Pension books", "optional")], labels)
    assert result.precision == Decimal(1)


def test_merged_certificates_cover_neither_label() -> None:
    labels = (
        Label(
            text="Marriage",
            type=("conditional",),
            must_contain=("marriage",),
            must_not_contain=("birth",),
        ),
        Label(
            text="Birth",
            type=("conditional",),
            must_contain=("birth",),
            must_not_contain=("marriage",),
        ),
    )
    item = _item("Marriage Certificate, Birth Certificate", "conditional", "if applicable")
    assert score([item], labels).recall == Decimal(0)


def test_wrong_type_lowers_type_accuracy() -> None:
    items = _perfect()
    items[0] = _item("Admission letter(s)", "optional")
    assert score(items, SAMPLE).type_accuracy == Decimal("0.8")


def test_wrong_condition_lowers_condition_accuracy() -> None:
    items = _perfect()
    items[3] = _item("Copies of the A-level exam degree", "conditional", "if rich")
    assert score(items, SAMPLE).condition_accuracy == Decimal(0)


def test_no_items_scores_zero_without_crashing() -> None:
    result = score([], SAMPLE)
    assert (result.precision, result.recall) == (Decimal(0), Decimal(0))
    assert not passes(result)


def test_hand_labels_load_for_each_labelled_source() -> None:
    labels = load_labels(LABELS)
    assert {k: sum(1 for x in v if x.required) for k, v in labels.items()} == {
        "de-cg-karachi-student-checklist": 18,
        "de-missions-pk-study-visa-page": 3,
        "de-missions-pk-tourist-visa-page": 20,
    }


def test_the_registry_tourist_entry_itself_meets_the_labels() -> None:
    # An independent check on the labels: the hand-written entry should satisfy them.
    items = [_item(r.text, r.type, r.condition) for r in entry(ISLAMABAD, "tourism").requirements]
    result = score(items, load_labels(LABELS)["de-missions-pk-tourist-visa-page"])
    assert result.missing == ()


def test_a_source_that_cannot_be_fetched_fails_the_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(url: str) -> None:
        raise OSError("refused")

    monkeypatch.setattr(extraction, "fetch", refuse)
    assert not evaluate(load_labels(LABELS), ExtractionModel("m"))
