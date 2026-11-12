"""The one way applicant text reaches a language model (R-27, ADR-0012).

Words this module doesn't know are treated as names: a memo loses a shop's name rather than
leak a person's. CNICs, phone numbers, account numbers and any other number become
placeholders, so no figure reaches the model either.
"""

import re

# Words common in Pakistani bank and platform memos, including Roman Urdu (ADR-0033).
MEMO_WORDS = frozenset(
    [
        "1LINK",
        "A/C",
        "ACC",
        "ACCOUNT",
        "ADVANCE",
        "ALERT",
        "AMMI",
        "ABBU",
        "ANNUAL",
        "ATM",
        "BACHON",
        "BANK",
        "BANKS",
        "BIJLI",
        "BILL",
        "BILLS",
        "BLOCKED",
        "BY",
        "CARD",
        "CASH",
        "CHARGES",
        "CHARGE",
        "CHEQUE",
        "CLEARING",
        "CR",
        "CREDIT",
        "DEBIT",
        "DEP",
        "DEPOSIT",
        "DR",
        "EASYPAISA",
        "ELECTRICITY",
        "FEE",
        "FEES",
        "FIVERR",
        "FOR",
        "FROM",
        "FT",
        "FUNDS",
        "GAS",
        "HBL",
        "HOME",
        "IBFT",
        "IN",
        "INC",
        "INTERNET",
        "INWARD",
        "JAMA",
        "JAZZCASH",
        "K-ELECTRIC",
        "KA",
        "KE",
        "KI",
        "KIRAYA",
        "KITAAB",
        "LLC",
        "LOAD",
        "LTD",
        "MAKAAN",
        "MCB",
        "MEEZAN",
        "MOBILE",
        "NAQD",
        "NET",
        "OF",
        "ON",
        "ONLINE",
        "OUTWARD",
        "OWN",
        "P2P",
        "PAYMENT",
        "PAYMENTS",
        "PAYONEER",
        "POS",
        "PRC",
        "PROFIT",
        "PTCL",
        "PURCHASE",
        "RAAST",
        "REF",
        "REFUND",
        "REMITTANCE",
        "RENT",
        "SALARY",
        "SCHOOL",
        "SERVICE",
        "SMS",
        "SNGPL",
        "STATIONERY",
        "SWIFT",
        "TAX",
        "TO",
        "TOPUP",
        "TRANSFER",
        "TUITION",
        "UBL",
        "UNIVERSITY",
        "UPWORK",
        "VIA",
        "WALLET",
        "WATER",
        "WHT",
        "WISE",
        "WITHDRAWAL",
        "WITHHOLDING",
        "ZAKAT",
    ]
)

_TOKEN = re.compile(
    r"(?P<CNIC>\b\d{5}-\d{7}-\d\b)"
    r"|(?P<PHONE>\+92[\s-]?3\d{2}[\s-]?\d{7}\b|\b03\d{2}[\s-]?\d{7}\b)"
    r"|(?P<ACCOUNT>\*+\d+|\b\d[\d-]{3,}\d\b)"
    r"|(?P<NUMBER>\d[\d,.]*(?![\w-]))"
    r"|(?P<WORD>[^\W_][\w/'-]*)"  # any script: an Urdu name is a name too
)
_NAMES = re.compile(r"\[NAME\](?:\s+\[NAME\])+")


def _placeholder(match: re.Match[str]) -> str:
    if match.lastgroup != "WORD":
        return f"[{match.lastgroup}]"
    return match.group() if match.group().upper() in MEMO_WORDS else "[NAME]"


def redact(text: str) -> str:
    """`text` with every name, CNIC, phone, account number and other number as a placeholder."""
    return _NAMES.sub("[NAME]", _TOKEN.sub(_placeholder, text))
