# Progress — PakkiFile

What's done lives in closed issues and merged PRs. This file holds only what they don't show. Keep each entry to one line.

## Waiting on owner

Q-1 to Q-15 settled 2026-10-30 (ADR-0012, 0030 to 0041; DESIGN.md; RULES R-22). Brief 05 questions settled 2026-11-10 (ADR-0049 to 0052).

- **Portal walk bonuses (ADR-0047).** Pick any of the four extra earning options listed in the ADR.
- **Rules gate on GitHub Models.** The `rules` CI job is disabled for zero spend. Later, switch `scripts/rules_gate.py` to GitHub Models (free tier via `GITHUB_TOKEN`) and re-enable it. Until then, `/code-review` against `docs/RULES.md` before every commit is the only rules check.


## Broke

- Brief 01: `.gitignore`'s `vault/` (meant for real documents) also hid `src/pakkifile/vault/`; anchored to `/vault/`. Caught in review before any push.

## Next

1. Brief 05: local evidence vault. `france-visas.gouv.fr` returned 403 from the runner.
2. Build portal walks (ADR-0047): `portal_walk` source authority, issue form, contributor ledger. Then complete the Islamabad study entry from a walk.
