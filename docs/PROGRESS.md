# Progress — PakkiFile

What's done lives in closed issues and merged PRs. This file holds only what they don't show. Keep each entry to one line.

## Waiting on owner

Q-1 to Q-15 settled 2026-10-30 (ADR-0012, 0030 to 0041; DESIGN.md; RULES R-22).

- **Portal walks (ADR-0047, Proposed).** Contributors walk portals the pipeline cannot read, for vesting points. Needs your call on its three open questions.
- **Rules gate on GitHub Models.** The `rules` CI job is disabled for zero spend. Later, switch `scripts/rules_gate.py` to GitHub Models (free tier via `GITHUB_TOKEN`) and re-enable it. Until then, `/code-review` against `docs/RULES.md` before every commit is the only rules check.


## Broke

- Brief 01: `.gitignore`'s `vault/` (meant for real documents) also hid `src/pakkifile/vault/`; anchored to `/vault/`. Caught in review before any push.

## Next

1. Brief 04: hosted checklist. `france-visas.gouv.fr` returned 403 from the runner.
2. Complete the German Embassy Islamabad study entry from a portal walk (ADR-0047); the checklist will link to the portal (#19, needs ADR-0048).
