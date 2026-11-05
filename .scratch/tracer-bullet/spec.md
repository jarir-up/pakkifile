# Spec: tracer bullet

Status: ready-for-agent
Serves: G-1, G-3, G-4 (brief 01).

## Problem Statement

No path yet connects an official source to a dossier. Until one thin path runs end to end, every later module is built against guesses about its neighbours.

## Solution

One crude path, run in CI, with an evaluation at each stage: the German Embassy Islamabad's study visa (D) page → three typed, cited requirements in the registry → a rendered checklist → one synthetic freelancer's bank statement → one figure computed by SQL → one M2 mismatch → a one-page dossier citing the figure.

## User Stories

1. As an applicant, I want the study visa (D) checklist for the German Embassy Islamabad, so that I know what to bring.
2. As an applicant, I want each requirement typed mandatory or conditional, so that I know what I can skip.
3. As an applicant, I want a conditional requirement to state its condition, so that I can tell whether it applies to me.
4. As an applicant, I want every requirement to cite its source page, section, URL, retrieval date and last-verified date, so that I can check it myself.
5. As a maintainer, I want the source's normalised text checksummed, so that a change is detectable.
6. As a maintainer, I want extraction scored against a hand-labelled checklist, so that a regression fails CI.
7. As an applicant, I want my statement loaded locally and a figure computed from it, so that numbers never come from a model.
8. As an applicant, I want the figure linked to the statement rows it came from, so that I can verify it.
9. As an applicant, I want an unexplained lump sum flagged as an M2 continuity mismatch against the requirement it concerns, so that I can explain it before an officer asks.
10. As a reviewing officer, I want a one-page dossier ordered like the checklist, with the figure cited to its rows, so that I can judge it quickly.
11. As the owner, I want the whole path to run in CI on synthetic data, so that every PR proves the path still works.
12. As the owner, I want synthetic evidence labelled synthetic, so that it is never mistaken for a real person's.

## Implementation Decisions

- Authority: German Embassy Islamabad. Application: study visa (D). Applicant profile: self-funded freelancer.
- Source: the missions' study visa page (pakistan.diplo.de, dated 27.11.2025), "Mandatory documents" section. The repo stores a short cited excerpt, not the page (ADR-0003). Live fetching belongs to the scheduled registry job (brief 03); the fetcher here is tested against a local server.
- Extraction is deterministic for the tracer: one list item → one requirement; "if applicable" text → conditional with that condition. Model extraction arrives in brief 03.
- Registry entries are YAML, one file per application (ADR-0040), validated by a Pydantic model that requires every R-21 citation field.
- Checklist and dossier render from the shared Jinja2 templates (ADR-0039) with DESIGN.md tokens.
- Statement rows load into Postgres; the figure is a parameterised SQL function in `figures`, money in integer minor units with a currency code (ADR-0027).
- Figure: largest credit with no identified counterparty, as a share of total credits in the statement period, plus its amount, linked to its row.
- Mismatch rule (crude): one credit with no identified counterparty that is at least 25% of total credits → M2 continuity, attached to the tuition-payment requirement, with a truthful risk sentence and no workaround advice.
- One command runs the path and prints per-stage evaluation results; CI runs it with a Postgres service.

## Testing Decisions

- Seams: the registry build (source excerpt in → validated registry entries out), the figure functions (statement in → figure with row links out), the mismatch check (requirements + figures in → findings out), and the end-to-end command (exit code and evaluation summary).
- Expected values come from the hand-labelled checklist and the generator's fact table, never recomputed the code's way.
- Postgres-backed tests run against a real database, not mocks.

## Out of Scope

Model extraction, scheduled fetching, confidence scoring, PDF ingestion, FastAPI routes, drafting letters, other missions.

## Further Notes

Depends on ADR-0042 (Proposed): PyYAML and psycopg.
