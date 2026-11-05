"""M2 continuity checks: funds an officer cannot trace to a source."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pakkifile.figures.continuity import UnattributedCredit, format_share
from pakkifile.registry.model import Requirement

MismatchKind = Literal["M1", "M2", "M3", "M4", "M5", "M6"]

# Crude tracer threshold; tuned against labelled cases in brief 07.
LUMP_SUM_SHARE = Decimal("0.25")


@dataclass(frozen=True)
class Finding:
    kind: MismatchKind
    requirement: Requirement
    figure: UnattributedCredit
    statement: str


def check_unattributed_credit(
    credit: UnattributedCredit | None, requirement: Requirement
) -> Finding | None:
    if credit is None or credit.share_of_credits < LUMP_SUM_SHARE:
        return None
    row = credit.rows[0]
    statement = (
        f"A credit of {credit.amount.display()} on {row.date.isoformat()} "
        f"({format_share(credit.share_of_credits)} of credits in this statement) "
        "has no identified sender. A reviewing officer may ask where these funds came from."
    )
    return Finding("M2", requirement, credit, statement)
