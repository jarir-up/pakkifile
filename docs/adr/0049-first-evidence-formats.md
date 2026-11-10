# ADR-0049: First statement formats: Payoneer and Meezan Bank PDF statements

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-11-10

## Context
Brief 05 parses statements on the applicant's machine. Real statements can't be used for development or evaluation, so the synthetic generator (ADR-0021) has to copy real layouts. Freelancer income usually lands on a platform first and then reaches a Pakistani bank, which issues the ePRC.

## Decision
The first two parsers read Payoneer's PDF statement and Meezan Bank's PDF account statement. The generator copies their structure, never anyone's data. Layouts as provided by the owner on 2026-11-10:

- **Meezan Bank** (from the owner's own statement). Header fields: account title, account number, IBAN, currency, from date, to date, opening balance, closing balance, address. Columns: Booking Date, Description, Credit, Debit, Available Balance.
- **Payoneer** (from a public sample on Scribd, document 788425026). Header fields: company header, address, primary account number, account currency, period, issuing date. Columns: Date, Description, Amount, Status, Running Balance.

Date and amount formats are not yet confirmed. The generator picks one format per layout and records it, and the first real statement that differs gets a parser fix and a regression test.

## Consequences
The money trail can be followed from the platform payout to the bank credit and its ePRC. Payoneer's CSV export, which has more columns, is a later parser. Revised 2026-11-10 from CSV to PDF for Payoneer, after the owner supplied the PDF layout.
