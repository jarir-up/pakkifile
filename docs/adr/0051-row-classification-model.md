# ADR-0051: Row classification model: qwen3:8b with thinking off

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-11-10

## Context
Rows the rule classifier can't place go to a local model, redacted (ADR-0012, ADR-0018). This runs on the applicant's machine, so download size and laptop CPU speed matter. ADR-0045 chose a model for extraction only.

## Decision
`qwen3:8b` (Apache-2.0) with thinking off is the first model scored for row classification. It is set through `PAKKIFILE_CLASSIFY_MODEL` and adopted only once it passes its evaluation on synthetic rows.

## Consequences
About a 5 GB download. Changing model is a configuration edit, re-scored by the evaluation.
