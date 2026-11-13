# ADR-0054: Payoneer's PDF statement before its CSV export

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-11-11

## Context
ADR-0049 chose Payoneer's CSV export. The layout the owner could supply on 2026-11-10 is Payoneer's PDF statement, from a public sample on Scribd (document 788425026). No source for the CSV's column order has been found.

## Decision
The first Payoneer parser reads the PDF statement. Header fields: company header, address, primary account number, account currency, period, issuing date. Columns: Date, Description, Amount, Status, Running Balance. The CSV parser follows once its layout has a source.

## Consequences
Amends ADR-0049 for Payoneer only. The PDF lacks the CSV's extra columns (Source, Target, Reference ID), so rows are deduplicated by fingerprint (ADR-0028).

## Owner note, 2026-11-13
A second public sample, supplied by the owner, shows the header as printed: the holder's name, address and phone on the left; "Account USD balance", "Period MM/DD/YYYY - MM/DD/YYYY" and "Issuing Date" on the right. It prints no account number and no company header text, so the vault names the account by its currency ("Payoneer USD").
