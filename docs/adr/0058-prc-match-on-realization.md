# ADR-0058: Match a certificate on its date of realization

- Status: Proposed

## Context
ADR-0057 matches a certificate to a statement credit booked up to 7 days before the certificate's date. A real e-PRC (a public Habib Metropolitan sample, 2026-11-12) is dated 26-Aug-2024 for proceeds realized on 29-May-2024. Banks issue certificates long after the money arrives, so that rule would leave real certificates unmatched.

## Decision
Amends ADR-0057's matching rule only. A certificate matches a statement credit of the same person with exactly the same PKR amount, booked from its date of realization to 3 days after it. When more than one credit matches, the nearest date wins, and each credit matches at most one certificate. `prc_certificate` also keeps the date of realization.

## Consequences
The 3-day window is a guess until a statement and a certificate for the same remittance can be compared.
