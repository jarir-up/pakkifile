# ADR-0043: Sources stored once, dated, and cited with a stance

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-10-30

## Context
FR-2 records each source's document, section, URL, retrieval date and last-verified date. Confidence must weigh recency (ADR-0007), but a document re-verified today can still be six years old: the Consulate General Karachi's student checklist was last modified 2020-01-07 and still asks for a €10,236 blocked account. Conflicts must be visible (ADR-0007), so a source can contradict a requirement as well as support it. A source shared by two missions is stored once (ADR-0038). Entries contributed by hand (ADR-0040) cite pages the pipeline has not fetched, so there is no fetched text to checksum.

## Decision
Sources live once in `registry-data/sources.yaml`, keyed by ID, each with document, URL, `published` (the date the document states or carries; empty when none), retrieved, last verified, source authority and an optional checksum (present whenever the pipeline fetched the text). A requirement cites sources by ID with a section and a stance (supports or conflicts, default supports), and must have at least one supporting citation. Recency uses the published date when known, otherwise the last-verified date.

## Consequences
Stale documents lower confidence even when re-verified. One source edit updates every mission that cites it. Hand-added sources lack change detection until the pipeline fetches them (brief 03).
