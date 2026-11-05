import csv
from pathlib import Path

from evaldata.statement import TRACER_FACTS, write_statement


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_same_seed_gives_identical_statement(tmp_path: Path) -> None:
    first = write_statement(TRACER_FACTS, seed=7, out_dir=tmp_path / "a")
    second = write_statement(TRACER_FACTS, seed=7, out_dir=tmp_path / "b")
    assert first.read_bytes() == second.read_bytes()


def test_statement_is_labelled_synthetic(tmp_path: Path) -> None:
    path = write_statement(TRACER_FACTS, seed=7, out_dir=tmp_path)
    assert "synthetic" in path.name
    assert {row["synthetic"] for row in _rows(path)} == {"true"}


def test_statement_honours_its_fact_table(tmp_path: Path) -> None:
    rows = _rows(write_statement(TRACER_FACTS, seed=7, out_dir=tmp_path))
    credits = [int(r["amount_minor"]) for r in rows if int(r["amount_minor"]) > 0]
    # Six client remittances of PKR 250,000 plus one PKR 900,000 cash deposit.
    assert sum(credits) == 240_000_000
    assert max(credits) == 90_000_000
    assert {r["currency"] for r in rows} == {"PKR"}
