"""Score the local row-classification model on the personas' memos (ADR-0051).

Every distinct persona memo, redacted as in the app, goes to the model with whether money
came in or out; its answer is compared with the memo's hand label. The rules are left out,
so this measures the model alone. Gates are proposed to the owner with the first numbers.

    PAKKIFILE_CLASSIFY_MODEL=qwen3:8b uv run python -m eval.classification
"""

import sys
import time
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from evaldata.persona import Persona, load_personas, transactions
from pakkifile.llm.classify_row import ClassifyModel, ModelClass, classify_memo
from pakkifile.llm.ollama import LocalModel, ModelError
from pakkifile.vault.classify import Direction, RowClass
from pakkifile.vault.review import REVIEW_BELOW


@dataclass(frozen=True)
class Item:
    memo: str
    direction: Direction
    label: RowClass


@dataclass(frozen=True)
class Score:
    total: int
    right: int
    unclassified: int  # left for the applicant: costs time, never a wrong figure
    confident_wrong: int  # a wrong class at or above REVIEW_BELOW: the error that matters most
    wrong: list[str]
    right_by_class: dict[str, tuple[int, int]]  # label: (right, of)
    seconds_per_row: float = 0.0


def items(personas: Iterable[Persona]) -> list[Item]:
    """Each distinct (memo, direction) once, with its label."""
    seen: dict[tuple[str, Direction], RowClass] = {}
    for persona in personas:
        for t in transactions(persona):
            direction: Direction = "credit" if t.amount_minor > 0 else "debit"
            seen.setdefault((t.description, direction), t.row_class)
    return [Item(memo, direction, label) for (memo, direction), label in seen.items()]


def score(cases: Sequence[tuple[Item, ModelClass]], seconds: float = 0.0) -> Score:
    wrong = [(i, got) for i, got in cases if got.row_class not in (None, i.label)]
    of = Counter(item.label for item, _ in cases)
    right = Counter(item.label for item, got in cases if got.row_class == item.label)
    return Score(
        total=len(cases),
        right=sum(right.values()),
        unclassified=sum(got.row_class is None for _, got in cases),
        confident_wrong=sum(got.confidence >= REVIEW_BELOW for _, got in wrong),
        wrong=[
            f"{i.memo} ({i.direction}): {got.row_class} at {got.confidence:.2f}, labelled {i.label}"
            for i, got in wrong
        ],
        right_by_class={label: (right[label], n) for label, n in sorted(of.items())},
        seconds_per_row=seconds / len(cases) if cases else 0.0,
    )


def evaluate(found: Sequence[Item], model: LocalModel) -> Score:
    started = time.monotonic()
    cases = [(item, classify_memo(item.memo, item.direction, model)) for item in found]
    return score(cases, time.monotonic() - started)


def main() -> None:
    try:
        result = evaluate(items(load_personas().values()), ClassifyModel.from_env())
    except ModelError as error:
        sys.exit(f"model unavailable: {error}")
    print(
        f"{result.right}/{result.total} right, {result.unclassified} unclassified, "
        f"{result.confident_wrong} wrong at or above {REVIEW_BELOW} confidence, "
        f"{result.seconds_per_row:.1f} s per row. No gate yet: the owner sets one."
    )
    for label, (right, of) in result.right_by_class.items():
        print(f"  {label}: {right}/{of}")
    print("\n".join(f"  wrong: {line}" for line in result.wrong))


if __name__ == "__main__":
    main()
