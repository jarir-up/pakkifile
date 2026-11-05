# Progress — PakkiFile

What's done lives in closed issues and merged PRs. This file holds only what they don't show. Keep each entry to one line.

## Waiting on owner

Q-1 to Q-15 settled 2026-10-30 (ADR-0012, 0030 to 0041; DESIGN.md; RULES R-22).


## Broke

- Brief 01: `.gitignore`'s `vault/` (meant for real documents) also hid `src/pakkifile/vault/`; anchored to `/vault/`. Caught in review before any push.

## Next

1. Owner creates the GitHub repo; then push `main`, `brief-00-wire-checks` and `brief-01-tracer` (stacked), open one PR each, and switch the tracker to GitHub issues. CI is unobserved until then.
2. Brief 02: registry model and confidence. Checklist rows lack the confidence DESIGN.md requires until it lands.
3. Live fetching needs a WebFetch allowlist for official domains in `.claude/settings.json`; the agent may not edit its own permissions.
