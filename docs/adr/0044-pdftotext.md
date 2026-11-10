# ADR-0044: pdftotext for reading official PDFs

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-11-09

## Context
Official checklists are often PDFs. The source pipeline needs their text to checksum and extract.

## Decision
Use `pdftotext` from the `poppler-utils` system package, called as a subprocess, for official source PDFs.

## Consequences
No Python dependency is added. The registry job installs `poppler-utils`. Scanned PDFs yield no text and need separate handling if one appears. Applicant PDFs (FR-10) are a separate decision.
