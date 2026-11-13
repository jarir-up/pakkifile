# ADR-0057: Where ePRC and S-PRC certificates are kept

- Status: Approved (owner, 2026-11-12)

## Context
Issue #35 reads ePRC and S-PRC certificates (FR-10) and links each to the statement credit it proves. FR-15 later checks statement totals against certificate totals. R-03 needs an approved ADR for the schema. No real certificate's layout has been supplied yet.

## Decision
- A `prc_certificate` table holds one row per remittance a certificate proves: person, evidence item, certificate number, issue date, remitter, foreign amount in minor units and its currency, the rate as a decimal, the PKR amount in minor units, the purpose, and `statement_row_id`, the matching credit (null when none matches).
- An S-PRC is one evidence item with several certificate rows.
- A certificate matches a statement credit of the same person with exactly the same PKR amount, booked up to 7 days before the certificate's date and never after it. When more than one credit matches, the nearest date wins, and each credit matches at most one certificate.
- A certificate with no match is stored with a null link and listed as unmatched. Nothing is dropped.

## Consequences
The rate is stored only as the certificate prints it, never used for arithmetic, because only `figures` computes money (R-20). The 7-day window is a guess until real certificates show how long a bank takes to issue one. The parser waits for one real ePRC's layout, its numbers replaced, as the Meezan parser did.

## Owner note, 2026-11-13
Many banks' e-PRCs leave the foreign amount, the rate or both blank or "N/A". Both are stored as null when the certificate gives none. The PKR amount is always present.
