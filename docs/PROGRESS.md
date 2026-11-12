# Progress — PakkiFile

What's done lives in closed issues and merged PRs. This file holds only what they don't show. Keep each entry to one line.

## Waiting on owner

Q-1 to Q-15 settled 2026-10-30 (ADR-0012, 0030 to 0041; DESIGN.md; RULES R-22). Brief 05 questions settled 2026-11-10 (ADR-0049 to 0052).

- **Portal walk bonuses (ADR-0047).** Pick any of the four extra earning options listed in the ADR.
- **ADR-0056 `needs_review`.** Built as: rows the rules place are not flagged; ambiguous rows are, until the model or the applicant decides. The ADR's "true until the applicant decides" could also mean every row. Confirm, or reword the ADR.
- **Model fallback (#33).** A model class under 0.8 confidence goes to review (`REVIEW_BELOW`); no ADR sets the number. The model is told whether money came in or went out, never the amount. Approve both or change them.
- **ADR-0057 (ePRC and S-PRC storage, #35).** Approve or edit; also send one real ePRC's text from `pdftotext -layout`, numbers replaced. The parser waits for both.
- **Vault gates (#37).** `uv run python -m eval.vault`, dev split, first numbers 2026-11-12: parse, stored-once and closing 100% for all three personas; rules right 100% / 100% / 97.8%, wrong 0, the student's sponsor transfer left ambiguous. Proposed gates: parse, stored-once and closing at 100%, rules wrong at 0. Approve or change. The test split waits for the persona review.
- **Rules gate on GitHub Models.** The `rules` CI job is disabled for zero spend. Later, switch `scripts/rules_gate.py` to GitHub Models (free tier via `GITHUB_TOKEN`) and re-enable it. Until then, `/code-review` against `docs/RULES.md` before every commit is the only rules check.



## Broke

- Brief 01: `.gitignore`'s `vault/` (meant for real documents) also hid `src/pakkifile/vault/`; anchored to `/vault/`. Caught in review before any push.

## Next

- Payoneer rows: confirm against one real statement (header lines, one row from `pdftotext -layout`). Guessed: "Label: value" header, "03 Apr 2026" dates, signed amounts, "Completed" status, oldest first. Any other status stops ingestion; keeping pending rows needs a status column (ADR).
- Sponsor names: ingestion passes none to the rules (the vault doesn't store them), so a named sponsor's transfer waits for review. Pass them once the vault holds sponsors.
- Nothing runs `vault.fallback.classify_pending` yet; the first runnable app (#34) calls it after ingestion. Redaction keeps names that match a known memo word (e.g. "Ammi", "Wise").
- Review page (#34): re-running rules must never overwrite a row the applicant decided (ADR-0056); `row_correction` is added there, where it is first written.

- Classifier rules are tuned on the persona memos (dev split). Write a held-out set of real-style memos (ADR-0029) before trusting its accuracy; ideally the owner writes it.
- Personas: owner reviews a set of 20 to 25 personas before the generation layer is built; three may be too narrow a sample (owner, 2026-11-11).

1. Brief 05: local evidence vault. `france-visas.gouv.fr` returned 403 from the runner.
2. Build portal walks (ADR-0047): `portal_walk` source authority, issue form, contributor ledger. Then complete the Islamabad study entry from a walk.
