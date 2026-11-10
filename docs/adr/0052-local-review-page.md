# ADR-0052: Uncertain rows are reviewed on a local web page

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-11-10

## Context
ADR-0018 sends low-confidence rows to review. The local app needs a review surface, and later readiness and dossier screens need the same app.

## Decision
The local app serves server-rendered pages (ADR-0039) with FastAPI (ADR-0013) on localhost only, run by uvicorn. The review page lists each uncertain row with its proposed class, which the applicant confirms or changes. Every correction is stored as evaluation data.

## Consequences
Adds `fastapi` and `uvicorn` as dependencies. The app binds to 127.0.0.1 and never serves the vault beyond the applicant's machine.
