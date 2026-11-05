# 06: One-page dossier, end-to-end command and CI

**What to build:** one command runs the whole path, writes a one-page dossier ordered like the checklist with the figure cited to its rows, and prints per-stage evaluation; CI runs it against a Postgres service.

**Blocked by:** 03, 05.

**Status:** done

- [x] Command exits non-zero if any stage's evaluation fails
- [x] Dossier cites every figure it shows
- [x] CI workflow runs the command
