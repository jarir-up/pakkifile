# ADR-0049: First statement formats: Payoneer CSV and Meezan Bank PDF

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-11-10

## Context
Brief 05 parses statements on the applicant's machine. Real statements can't be used for development or evaluation, so the synthetic generator (ADR-0021) has to copy real layouts. Freelancer income usually lands on a platform first and then reaches a Pakistani bank, which issues the ePRC.

## Decision
The first two parsers are Payoneer's CSV transaction export and Meezan Bank's PDF account statement. The generator copies their structure (columns, headers, date and amount formats, page furniture), never anyone's data. Each layout cites where its structure came from.

## Consequences
The money trail can be followed from the platform payout to the bank credit and its ePRC. Other platforms and banks are added as parsers later, one per format.
