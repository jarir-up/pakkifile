# ADR-0030: The registry is data in git, built by scheduled jobs and served as a static site

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-10-30

## Context
A hosted server with a database and review queue meant running and paying for infrastructure, and kept an endpoint alive that could receive personal data. The registry is meant to be versioned and reviewed by exception (ADR-0007).

## Decision
Registry entries live as data files in the repo. A scheduled GitHub Actions job fetches official sources, extracts requirements and opens a pull request when a source changes. Entries that pass the auto-publish rule (ADR-0036) merge automatically; conflicts and low-confidence entries wait in the PR for a maintainer. CI builds the checklist as a static site on GitHub Pages. The local app pulls the same data files.

## Consequences
Git history is the record of what changed and when. The review queue is the list of open registry PRs. Hosting is free and there is no server to run. pgvector is used only in the local app. Supersedes ADR-0022. With ADR-0012, extraction uses a local Ollama model on the free CPU runner (owner, 2026-11-05); if that proves too slow or too weak, it runs on a maintainer's machine instead.
