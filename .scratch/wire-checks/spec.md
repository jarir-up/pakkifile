# Spec: wire scripts/check.sh

Status: ready-for-agent
Serves: all goals (brief 00).

## Problem Statement

Every agent, hook and CI run calls `scripts/check.sh`, but it has no checks, so nothing is verified and CI fails by design.

## Solution

Fill the fast and slow checks for the approved stack (ADR-0013) and give CI a Python setup step, so "it passed" means lint, types, tests and build passed.

## User Stories

1. As a coding agent, I want fast checks (lint, format, types) after every edit, so that I fix mistakes while they are small.
2. As a coding agent, I want full checks (plus tests and build) before I finish a turn, so that I never hand over a broken tree.
3. As the owner, I want CI to run the same script, so that a green PR means the same thing locally and in CI.
4. As the owner, I want CI to fail when a lint error is introduced, so that the gate is real.
5. As a contributor, I want one command to install the toolchain, so that I can run the checks without guessing versions.

## Implementation Decisions

- uv manages Python 3.12 and a locked dev group: ruff, mypy, pytest. No runtime dependencies yet.
- Package in a src layout under the `pakkifile` name, built with uv's own build backend so the build check adds no dependency.
- Fast: ruff lint, ruff format check, mypy strict. Slow: pytest, package build.
- All commands run with the lockfile frozen, so CI and local resolve identically.
- CI installs uv, syncs, then calls `scripts/check.sh`.

## Testing Decisions

- A smoke test imports the package; it is the seed of the suite.
- The gate itself is verified by running the script on a clean tree (passes) and on a tree with an injected lint error (fails).

## Out of Scope

Application code, Postgres in CI, evaluation gates (brief 01).

## Further Notes

CI cannot be observed until the GitHub repo exists; local runs of the script stand in until then.
