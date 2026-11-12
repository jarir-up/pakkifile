"""Rule classification of statement rows, before any model (ADR-0018, FR-11).

Rules never guess: a row no rule matches, or that rules of different classes match, is
ambiguous and goes to the model and then to review. Keyword lists include common Roman Urdu
memo terms (ADR-0033). Each rule only applies in its direction: a credit is never spending.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict

RowClass = Literal[
    "client_payment",  # a counterparty pays the applicant on a platform (GLOSSARY)
    "platform_withdrawal",  # money leaves the platform for the applicant's bank
    "remittance_in",  # a foreign credit reaches the bank
    "sponsor_transfer",
    "cash_deposit",
    "own_transfer",
    "fee",
    "tax",
    "spending",
]
Direction = Literal["credit", "debit"]
# A platform (Payoneer) statement or a bank statement: some rows only make sense on one.
AccountKind = Literal["platform", "bank"]
ClassSource = Literal["rule", "model", "applicant"]  # the applicant's decision always wins


@dataclass(frozen=True)
class Rule:
    name: str
    row_class: RowClass
    direction: Direction
    pattern: re.Pattern[str]
    account: AccountKind | None = None  # None: either kind of statement


def _rule(
    name: str,
    row_class: RowClass,
    direction: Direction,
    *words: str,
    account: AccountKind | None = None,
) -> Rule:
    return Rule(name, row_class, direction, re.compile("|".join(words), re.IGNORECASE), account)


RULES = (
    # "IBFT INWARD" is a domestic transfer, so INWARD alone is not enough.
    _rule(
        "remittance",
        "remittance_in",
        "credit",
        r"\bHOME REMITTANCE\b",
        r"\bINWARD (SWIFT|REMITTANCE)\b",
        r"\bPRC\b",
    ),
    _rule("client payment", "client_payment", "credit", r"\bPayment from\b", account="platform"),
    _rule(
        "platform withdrawal",
        "platform_withdrawal",
        "debit",
        r"\bWithdrawal to\b",
        account="platform",
    ),
    # abbu, ammi: father, mother. Not "walid", which is also a common given name.
    _rule("parent", "sponsor_transfer", "credit", r"\b(abbu|ammi)\b"),
    _rule("cash deposit", "cash_deposit", "credit", r"\bCASH DEP", r"\bnaqd jama\b"),
    _rule("own account", "own_transfer", "debit", r"\bto own\b", r"\bBLOCKED ACCOUNT\b"),
    _rule(
        "bank fee",
        "fee",
        "debit",
        r"\b(annual|service|account|sms|withdrawal) (account |alert )?(fee|charges)\b",
        r"\bBANK CHARGES\b",
    ),
    _rule("tax", "tax", "debit", r"\bWITHHOLDING TAX\b", r"\bWHT\b", r"\b236P\b"),
    # kiraya: rent; bijli: electricity; bill; kitaab: book; bachon ki: children's.
    _rule(
        "household",
        "spending",
        "debit",
        r"\bkiraya\b",
        r"\bbijli\b",
        r"\bbill\b",
        r"\bmobile load\b",
        r"\bATM CASH WITHDRAWAL\b",
        r"\bschool fees\b",
        r"\bTUITION\b",
        r"\bkitaab",
        r"\bstationery\b",
    ),
)


def _sponsor_rule(name: str) -> Rule:
    """A credit naming a sponsor, as whole words: "ALI" must not match "KHALID"."""
    return _rule("named sponsor", "sponsor_transfer", "credit", rf"\b{re.escape(name)}\b")


@dataclass(frozen=True)
class RuleResult:
    """The class the rules agree on, or None when no rule or disagreeing rules matched."""

    row_class: RowClass | None
    rules: tuple[str, ...]


def classify(
    description: str,
    amount_minor: int,
    account: AccountKind = "bank",
    sponsors: Sequence[str] = (),
) -> RuleResult:
    """Classify one row. `sponsors` are the names of the applicant's sponsors in the vault."""
    direction: Direction = "credit" if amount_minor > 0 else "debit"
    rules = [*RULES, *(_sponsor_rule(name) for name in sponsors)]
    matched = [
        (rule.name, rule.row_class)
        for rule in rules
        if rule.direction == direction
        and rule.account in (None, account)
        and rule.pattern.search(description)
    ]
    classes = {row_class for _, row_class in matched}
    names = tuple(name for name, _ in matched)
    return RuleResult(classes.pop() if len(classes) == 1 else None, names)


class ClassColumns(TypedDict):
    row_class: RowClass | None
    class_source: ClassSource | None
    needs_review: bool


def rule_columns(description: str, amount_minor: int, account: AccountKind) -> ClassColumns:
    """A row's class at ingestion (ADR-0056): rules only. Every row waits for the applicant.

    Sponsor names aren't in the vault yet, so a named sponsor's transfer waits too.
    """
    row_class = classify(description, amount_minor, account).row_class
    return {
        "row_class": row_class,
        "class_source": "rule" if row_class else None,
        "needs_review": True,  # owner, 2026-11-12: every row, until the applicant decides
    }
