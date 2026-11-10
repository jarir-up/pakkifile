# ADR-0048: An entry records where its full list lives

- Status: Proposed

## Context
Some sources publish only part of a list. The German Embassy Islamabad study page lists 3 items, and the rest appear after the questionnaire at https://digital.diplo.de/studium. Applicants reading our 3 rows could take them as the whole list. The owner approved showing a notice on 2026-11-10. The entry format has no place to record it (R-03).

## Decision
A registry entry may carry `full_list: {name, url}`, which a maintainer adds by hand. The checklist shows `Full list: <name>` as a link above the table when it is set. The pipeline never writes it, and comparisons between built and published entries ignore it.

## Consequences
One optional field in the entry files. When a portal walk (ADR-0047) completes a list, the maintainer removes the field.
