# Progress — PakkiFile

What's done lives in closed issues and merged PRs. This file holds only what they don't show. Keep each entry to one line.

## Waiting on owner

Q-1 to Q-15 settled 2026-10-30 (ADR-0012, 0030 to 0041; DESIGN.md; RULES R-22). Brief 05 questions settled 2026-11-10 (ADR-0049 to 0052) and 2026-11-12 (ADR-0057, model fallback, vault gates, one Save, page guards, every row reviewed).

- **Portal walk bonuses (ADR-0047).** Pick any of the four extra earning options listed in the ADR.
- **Migrations now (ADR-0055).** The owner is starting to store real files. The app only creates missing tables, so any later column change breaks a vault that holds data (it happened with an empty one on 2026-11-13). Proposal: bring Alembic forward from "first local release" to now. Approve, and I'll write the ADR amendment and the first migration.
- **ADR-0059 (held-out layouts).** Written from the owner's persona review of 2026-11-13: a held-out layout is a template change of a bank already read. Approve or edit.
- **HBL statement layout (persona 12).** Paste a header and one row from `pdftotext -layout`, values replaced; the HBL parser waits for it.
- **Rules gate on GitHub Models.** The `rules` CI job is disabled for zero spend. Later, switch `scripts/rules_gate.py` to GitHub Models (free tier via `GITHUB_TOKEN`) and re-enable it. Until then, `/code-review` against `docs/RULES.md` before every commit is the only rules check.



## Broke

- 2026-11-13: the local vault kept an old `prc_certificate` table, and the tests reused it. Tests now build their tables in a schema of their own that vanishes at rollback. The empty stale table was dropped and recreated.
- 2026-11-12: tests and the local vault share one database. Tests that counted every row failed once the vault held data (a demo ingest). All counts are now scoped to the test's own person or row; the suite passed with the demo data present before it was deleted.
- Brief 01: `.gitignore`'s `vault/` (meant for real documents) also hid `src/pakkifile/vault/`; anchored to `/vault/`. Caught in review before any push.

## Next

- Payoneer rows: confirm against one real statement (header lines, one row from `pdftotext -layout`). Guessed: "Label: value" header, "03 Apr 2026" dates, signed amounts, "Completed" status, oldest first. Any other status stops ingestion; keeping pending rows needs a status column (ADR).
- Sponsor names: ingestion passes none to the rules (the vault doesn't store them), so a named sponsor's transfer waits for review. Pass them once the vault holds sponsors.
- Nothing runs `vault.fallback.classify_pending` yet; the first runnable app (#34) calls it after ingestion. Redaction keeps names that match a known memo word (e.g. "Ammi", "Wise").
- Review page (#34): re-running rules must never overwrite a row the applicant decided (ADR-0056); `row_correction` is added there, where it is first written.

- Classifier rules are tuned on the persona memos (dev split). Write a held-out set of real-style memos (ADR-0029) before trusting its accuracy; ideally the owner writes it.
- Personas: the owner reviewed the drafts on 2026-11-13; `evaldata/personas/DRAFTS.md` holds the revised 24. Write each as YAML once approved.

1. Brief 05: local evidence vault. `france-visas.gouv.fr` returned 403 from the runner.
2. Build portal walks (ADR-0047): `portal_walk` source authority, issue form, contributor ledger. Then complete the Islamabad study entry from a walk.
