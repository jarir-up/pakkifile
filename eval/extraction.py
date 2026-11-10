"""Score model extraction against hand-labelled sources (brief 03).

Scoring is pure, so PR CI tests it without a model. Running it needs Ollama:

    PAKKIFILE_EXTRACTION_MODEL=qwen3:14b PAKKIFILE_EXTRACTION_THINK=off \
        uv run python -m eval.extraction
"""

import difflib
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from pakkifile.llm.extract import ExtractionError, ExtractionModel, extract_requirements
from pakkifile.registry.files import SOURCES_FILE, load_sources
from pakkifile.registry.model import ExtractedItem, RequirementType
from pakkifile.sources.check import REGISTRY
from pakkifile.sources.fetch import FETCH_FAILURES, fetch

LABELS = Path("evaldata/labels/extraction")
GATES = {
    "precision": Decimal("0.90"),
    "recall": Decimal("0.95"),
    "type_accuracy": Decimal("0.90"),
    "condition_accuracy": Decimal("0.75"),
    "numbers_exact": Decimal("1"),
}


class Label(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    type: tuple[RequirementType, ...]
    must_contain: tuple[str, ...]
    must_not_contain: tuple[str, ...] = ()
    condition_contains: str | None = None
    required: bool = True


@dataclass(frozen=True)
class ExtractionResult:
    precision: Decimal
    recall: Decimal
    type_accuracy: Decimal
    condition_accuracy: Decimal
    numbers_exact: Decimal
    missing: tuple[str, ...]
    extra: tuple[str, ...]


def _norm(text: str) -> str:
    """Lower case, no thousands separators, one spelling for school levels."""
    # Capitals only: "at a level of B2" is not an A-level.
    spelled = re.sub(r"\b([OA]) level", r"\1-level", text)
    without_separators = re.sub(r"(?<=\d)[., ](?=\d{3}\b)", "", spelled.lower())
    return " ".join(without_separators.split())


def _contains(text: str, fact: str) -> bool:
    if fact.isdigit():  # "30000" must not match "300000".
        return re.search(rf"(?<!\d){fact}(?![.,]?\d)", text) is not None
    return fact in text


def _matches(item: ExtractedItem, label: Label) -> bool:
    text = _norm(f"{item.text} {item.condition or ''}")
    return all(_contains(text, _norm(fact)) for fact in label.must_contain) and not any(
        _contains(text, _norm(fact)) for fact in label.must_not_contain
    )


def _ratio(part: int, whole: int) -> Decimal:
    return Decimal(part) / Decimal(whole) if whole else Decimal(1)


def score(items: Sequence[ExtractedItem], labels: Sequence[Label]) -> ExtractionResult:
    # Each item pairs with one label; the closest wording wins when several could match.
    pairs = sorted(
        (
            (-difflib.SequenceMatcher(None, _norm(item.text), _norm(label.text)).ratio(), i, j)
            for i, item in enumerate(items)
            for j, label in enumerate(labels)
            if _matches(item, label)
        ),
    )
    matched: dict[int, int] = {}
    for _, i, j in pairs:
        if i not in matched and j not in matched.values():
            matched[i] = j
    found = set(matched.values())
    required = [j for j, label in enumerate(labels) if label.required]
    typed = sum(1 for i, j in matched.items() if items[i].type in labels[j].type)
    with_condition = [
        (items[i], condition)
        for i, j in matched.items()
        if (condition := labels[j].condition_contains)
    ]
    conditioned = sum(1 for item, want in with_condition if want in _norm(item.condition or ""))
    numeric = [j for j in required if any(fact.isdigit() for fact in labels[j].must_contain)]
    return ExtractionResult(
        precision=_ratio(len(matched), len(items)) if items else Decimal(0),
        recall=_ratio(sum(1 for j in required if j in found), len(required)),
        type_accuracy=_ratio(typed, len(matched)),
        condition_accuracy=_ratio(conditioned, len(with_condition)),
        numbers_exact=_ratio(sum(1 for j in numeric if j in found), len(numeric)),
        missing=tuple(labels[j].text for j in required if j not in found),
        extra=tuple(item.text for i, item in enumerate(items) if i not in matched),
    )


def passes(result: ExtractionResult) -> bool:
    return all(getattr(result, metric) >= gate for metric, gate in GATES.items())


def load_labels(root: Path) -> dict[str, tuple[Label, ...]]:
    return {
        path.stem: tuple(Label.model_validate(item) for item in yaml.safe_load(path.read_text()))
        for path in sorted(root.glob("*.yaml"))
    }


def _report(source_id: str, result: ExtractionResult) -> Iterable[str]:
    verdict = "PASS" if passes(result) else "FAIL"
    metrics = " ".join(f"{metric}={getattr(result, metric):.2f}" for metric in GATES)
    yield f"{verdict}  {source_id} {metrics}"
    yield from (f"  missing: {text}" for text in result.missing)
    yield from (f"  extra: {text}" for text in result.extra)


def evaluate(labels: Mapping[str, Sequence[Label]], model: ExtractionModel) -> bool:
    sources = load_sources(REGISTRY / SOURCES_FILE)
    passed = True
    for source_id, source_labels in labels.items():
        try:
            items = extract_requirements(fetch(sources[source_id].url).text, model)
        except (ExtractionError, *FETCH_FAILURES) as error:
            print(f"FAIL  {source_id} {error}")
            passed = False
            continue
        result = score(items, source_labels)
        print("\n".join(_report(source_id, result)), flush=True)
        passed = passed and passes(result)
    return passed


def main() -> None:
    if not evaluate(load_labels(LABELS), ExtractionModel.from_env()):
        sys.exit(1)


if __name__ == "__main__":
    main()
