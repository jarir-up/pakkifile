# 01: Wire fast and slow checks for the Python stack

**What to build:** `scripts/check.sh` runs ruff, ruff format, mypy, pytest and a package build through uv, and CI runs it after installing uv.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `./scripts/check.sh` passes on a clean tree
- [x] `./scripts/check.sh --fast` fails when a lint error is introduced
- [x] CI workflow installs uv and Python 3.12 before running the script
- [x] The run-the-app row in AGENTS.md stays unset (no runnable app yet)
