# Architecture — PakkiFile

Two surfaces, one codebase:

- **Registry** (public): data files in this repo, kept current by scheduled GitHub Actions jobs and published as a static checklist site on GitHub Pages. No server, no personal data (ADR-0030).
- **Local app** (runs on the applicant's machine): evidence vault, figures, mismatch engine, readiness agent, dossier export. Downloads the whole registry (ADR-0041); sends nothing personal anywhere except redacted snippets to a language model.

## Stack

From approved ADRs. Versions are verified when each dependency is added.

| Concern | Choice | ADR |
|---|---|---|
| Language and API | Python 3.12, FastAPI, Pydantic v2 | 0013 |
| Persistence | SQLAlchemy 2 with Alembic; Postgres with pgvector and built-in full-text search | 0013, 0014 |
| Tooling | uv, ruff, mypy, pytest | 0013 |
| Agent orchestration | LangGraph for the readiness agent; retrieval and checks as plain Python and SQL | 0015 |
| Embeddings and reranking | Local open models | 0016 |
| Language model | Local model via Ollama for all LLM work; hosted model optional and off by default; drafts use placeholders | 0012 |
| Tracing | Langfuse, self-hosted, development and CI only | 0034 |
| Pages | Jinja2 templates, no JavaScript framework; static build for the checklist, served live by the local app | 0039 |
| Local packaging | `docker compose` for v0 | 0032 |
| CI | GitHub Actions: `scripts/check.sh`; the rules gate is disabled for zero spend | 0023, 0012 |
| Hosting | GitHub Pages for the checklist site | 0030 |

Licence: AGPL-3.0 for code, CC BY-SA 4.0 for registry data (ADR-0031).

## Folder map

```
registry-data/  YAML, one file per application; community stories (ADR-0040)
src/pakkifile/
  registry/     requirement model, confidence scoring, auto-publish rule
  sources/      fetch, checksum, change detection, extraction of official documents
  vault/        ingestion of applicant documents (statements, ePRC, returns, invoices)
  figures/      money rules and parameterised SQL figure functions
  mismatch/     checks M1 to M6, evidence vs requirements and evidence vs evidence
  readiness/    LangGraph agent, drafting, approval gate
  dossier/      ordering, citation index, export
  llm/          model interface, redaction, prompts
  web/          Jinja2 templates and FastAPI routes; static checklist build
evaldata/       synthetic generator and labelled sets (frozen splits are harness-only)
eval/           evaluation harness and reports
tests/
```

## Module boundaries

- `registry` and `sources` never import from `vault`, `figures`, `mismatch`, `readiness` or `dossier`. The checklist site is built from these two only, which is how R-22 stays true.
- Only `figures` computes money. Others call it; nothing else does arithmetic on amounts (R-20, R-24).
- Only `llm` talks to a language model, and only through its redaction function (R-27).
- `readiness` orchestrates the other modules; nothing imports `readiness`.
- Only the evaluation harness reads frozen test and adversarial data (R-26).

## Data flow

**Registry pipeline (GitHub Actions):**
1. Weekly, fetch each official source and checksum its normalised text (ADR-0036).
2. On change, extract requirements into the typed schema with citations and open a pull request.
3. Compute confidence from source authority, recency and agreement.
4. Auto-merge entries that pass the auto-publish rule; the rest wait in the PR for a maintainer.
5. Build the static checklist site by authority, application and applicant profile.

**Applicant flow (local):**
1. The app downloads the whole registry; the applicant picks a target application and profile, and the app selects the matching checklist locally.
2. Documents go into the local vault and are parsed deterministically; only ambiguous rows reach the model, redacted.
3. `figures` computes totals with SQL and links each to source rows and pages.
4. `mismatch` checks evidence against requirements and against itself, labelling each finding M1 to M6.
5. `readiness` drafts letters with placeholders that local code fills, and waits for the applicant's approval on each.
6. `dossier` exports an indexed file ordered for the reviewing officer.

## External services

| Service | Use | Credentials |
|---|---|---|
| Official sources (embassy, VFS, BLS, SBP, FBR pages and PDFs) | Registry input | None; public |
| Ollama (local) | Requirement extraction, ambiguous-row classification, drafting | None |
| Hosted model (optional, off by default) | Same, when configured | Key from env, never committed |
| GitHub | Code, issues, CI | None |

## Decisions

Decisions are ADRs in `docs/adr/`, one file each. Only the owner sets an ADR's status to Approved.
