# ADR-0047: Contributors walk portals the pipeline cannot read

- Status: Proposed

## Context
Some authorities publish their full list only behind an interactive portal. The German Embassy Islamabad study page lists 3 items; the rest appear after the questionnaire at https://digital.diplo.de/studium. The pipeline cannot answer a questionnaire, so that part of the registry stays unverified. Issue #19 links the checklist to the portal meanwhile.

## Decision
- A contributor (U3) takes a portal walk: answers the questionnaire as one applicant profile and records the list it shows.
- Walks come through the ADR-0040 issue form with structured fields only: authority, application, the answers chosen, date walked, each document as shown, and the portal's own printout or saved page with personal details removed.
- A maintainer (U7) checks the list against the evidence, stores the evidence as a source document and cites it as a `consulate_page` source verified on the walk date. Walks age under the normal recency rule.
- Each accepted walk earns points in a public ledger, `registry-data/contributors.yaml`, keyed by GitHub handle. Points vest when another contributor's independent walk confirms the same list, so accuracy pays and contributors come back to confirm each other's walks.
- Points carry no money value (PRD non-goals). They show as credit on the rows a walk verified.

## Consequences
No accounts or receiving endpoint; contributing still needs a GitHub account. A single unconfirmed walk scores High confidence like any consulate page, so the maintainer's evidence check is the guard until a second walk confirms it.

## Open for the owner
1. Rank walks as `consulate_page`, or add a lower source authority for them.
2. What points unlock beyond credit.
3. The vesting rule: confirmation by another walk, or also returning within a set time.
