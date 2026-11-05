# AGENTS.md — PakkiFile

This file is the entry point for every coding agent in this repo. Read it first, every session.

## Standing instructions

Cut taglines, helper text and secondary labels. If a screen needs them to make sense, fix the layout.

Make the best decision that will elevate all three: the user experience (UX), developer experience (DX), and agent experience (AX) always, without breaking anything.

And then finally Before you add code for a race condition or security edge case that is unlikely or purely hypothetical, tell me exactly what would go wrong, how likely that is, and how much complexity the extra code adds, in words a 10-year-old could understand. Then wait for my OK. Don't quietly widen the scope to guard against problems that only exist in theory.

## Who decides what

- The product owner approves every design and architecture decision. Approved decisions are the ADRs in `docs/adr/` with `Status: Approved`.
- You implement approved decisions. You may write an ADR as `Proposed`, but never mark one approved and never build on an unapproved one.
- If implementation shows a decision is wrong, stop that issue, write the problem and your proposed change under "Waiting on owner" in `docs/PROGRESS.md`, and move to an issue that doesn't depend on it.

## Where things live

Each kind of information has one home. Don't copy it anywhere else.

| What | Where | Who edits it |
|---|---|---|
| Product: what we build and for whom | `docs/PRD.md` | Owner |
| Stack, folders, module boundaries, data flow | `docs/ARCHITECTURE.md` | Owner |
| Decisions | `docs/adr/` | Owner approves; you may propose |
| Colors, type, components, feel | `docs/DESIGN.md` | Owner |
| Rules machines can't check; CI enforces them | `docs/RULES.md` | Owner |
| Domain terms | `GLOSSARY.md` | You and owner |
| Feature PRDs and tasks | GitHub issues | Created through the skills below |
| Broke, next, waiting on owner | `docs/PROGRESS.md` | You, every issue |

Read PRD, ARCHITECTURE, DESIGN, RULES and the approved ADRs before your first issue in a session. After that, read only what an issue touches. This repo's coding standards are `docs/RULES.md`; any skill that checks standards uses that file.

## Workflow

This repo uses Matt Pocock's skills. The skills' own setup section below records the tracker and doc layout.

1. **Plan a feature**: `/grill-with-docs` with the owner until every branch of the plan is resolved, then `/to-spec`. A feature PRD names the `docs/PRD.md` goal or requirement it serves. If it serves none, stop and ask the owner.
2. **Slice it**: `/to-tickets` turns the feature PRD into vertical-slice issues with acceptance criteria.
3. **Build one issue at a time**: `/tdd` on the next unblocked issue. For a bug, `/diagnosing-bugs` first, then a regression test that fails without the fix.
4. **Verify**: `./scripts/check.sh` must pass. Then `/code-review` against the issue and `docs/RULES.md`, and fix what it finds before opening the PR.
5. **Close out**: one PR per issue, with `Closes #<n>` in the description. Add one line to PROGRESS.md for anything that broke or is now next.

Don't install skills that duplicate what this repo already does. `.claude/settings.json` already blocks destructive git commands, so skip `git-guardrails-claude-code`.

## Commands

| Purpose | Command |
|---|---|
| All checks (lint, types, tests, build) | `./scripts/check.sh` |
| Fast checks only (lint, types) | `./scripts/check.sh --fast` |
| Start the local database (tests need it) | `docker compose up -d --wait db` |
| Run the app locally | Set by the first issue that adds a runnable app; record the command here |

Hooks run the fast checks after each edit and the full checks before you finish a turn with uncommitted changes. When a hook reports a failure, fix the cause; don't silence the check.

## Permissions

Pushing, installing dependencies and network calls ask for approval, except fetching from the official source domains allowed in `.claude/settings.json`. Secrets and destructive commands are blocked. See `.claude/settings.json`. Adding a dependency also needs an approved ADR (RULES R-02).

## Merging

Every pull request passes `./scripts/check.sh` in CI. The second gate, a model reviewing the diff against `docs/RULES.md`, is disabled while the project runs on zero spend (see `docs/PROGRESS.md`); until it returns, `/code-review` against `docs/RULES.md` before every commit stands in. To accept a flagged violation on purpose, the owner adds `waive R-07: <reason>` to the PR description. Never add waivers yourself.

## Agent skills

### Issue tracker

GitHub issues. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default role labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. See `docs/agents/domain.md`.
