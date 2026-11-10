# ADR-0047: Contributors walk portals the pipeline cannot read

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-11-10

## Context
Some authorities publish their full list only behind an interactive portal. The German Embassy Islamabad study page lists 3 items; the rest appear after the questionnaire at https://digital.diplo.de/studium. The pipeline cannot answer a questionnaire, so that part of the registry stays unverified. Issue #19 links the checklist to the portal meanwhile (ADR-0048).

## Decision
- A contributor (U3) takes a portal walk: answers the questionnaire as one applicant profile and records the list it shows.
- Walks come through the ADR-0040 issue form with structured fields only: authority, application, the answers chosen, date walked, each document as shown, and the portal's own printout or saved page with personal details removed.
- A maintainer (U7) checks the list against the evidence, stores the evidence as a source document and cites it with the source authority `portal_walk`, ranked below a consulate page and above a service-provider page. Walks age under the normal recency rule.
- Each accepted walk earns points in a public ledger, `registry-data/contributors.yaml`, keyed by GitHub handle. Points vest when either happens: another contributor's independent walk confirms the same list, or the contributor returns with another accepted walk within 90 days.
- Points carry no money value (PRD non-goals) and unlock nothing beyond credit on the rows a walk verified. Redeemable tokens are shelved.

## Consequences
No accounts or receiving endpoint; contributing still needs a GitHub account. `portal_walk` adds a step to the source authority order and its weight to confidence. A single unconfirmed walk scores below a consulate page, and the maintainer's evidence check stays the main guard.

## Open for the owner
Extra ways to earn or vest points, none adopted yet:
1. **First walk:** the first accepted walk of a portal nobody has walked earns double.
2. **Freshness bounty:** a walk that re-verifies a list older than 90 days earns extra, which serves the PRD's 90-day re-verification measure.
3. **Change spotter:** a confirmed walk that shows the portal's list has changed earns a bonus.
4. **Streak:** accepted walks in consecutive months vest faster.
