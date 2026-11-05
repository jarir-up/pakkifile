# Progress — PakkiFile

What's done lives in closed issues and merged PRs. This file holds only what they don't show. Keep each entry to one line.

## Waiting on owner

Q-1 to Q-15 settled 2026-10-30 (ADR-0012, 0030 to 0041; DESIGN.md; RULES R-22).

- **Rules gate on GitHub Models.** The `rules` CI job is disabled for zero spend. Later, switch `scripts/rules_gate.py` to GitHub Models (free tier via `GITHUB_TOKEN`) and re-enable it. Until then, `/code-review` against `docs/RULES.md` before every commit is the only rules check.
- **Where model extraction runs (brief 03).** ADR-0030 runs extraction in a scheduled GitHub Actions job, but ADR-0012 makes the model a local Ollama one. Recommend: the scheduled job runs a small Ollama model on the free CPU runner and only opens PRs; if that proves too slow or too weak, extraction runs on a maintainer's machine instead.


## Broke

- Brief 01: `.gitignore`'s `vault/` (meant for real documents) also hid `src/pakkifile/vault/`; anchored to `/vault/`. Caught in review before any push.

## Next

1. Review and merge the stacked PRs for #1, #2 and #3 in order; CI runs on each.
2. Brief 02: registry model and confidence. Checklist rows lack the confidence DESIGN.md requires until it lands.
