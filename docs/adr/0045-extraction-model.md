# ADR-0045: Extraction model: qwen3:14b with thinking off

- Status: Proposed
- Approved by: Not yet approved.

## Context
ADR-0012 makes a local Ollama model the default. Trial run 42581925745 compared four setups on GitHub's free 4-CPU, 16 GB runner, on three official documents: the Consulate General Karachi checklist, and the missions' tourist and study visa pages. Requirement extraction only reads public documents in a scheduled job, so speed matters little and a wrong requirement matters a lot.

## Decision
Proposed: `qwen3:14b` (Apache-2.0) with thinking off extracts requirements, set through `PAKKIFILE_EXTRACTION_MODEL` and `PAKKIFILE_EXTRACTION_THINK`. This choice covers extraction only. Models that run on applicants' machines are chosen separately.

## Consequences
It was the only setup to return the right items on all three documents, at about 15 minutes of extraction per full run and a 9.3 GB download. Changing model is a configuration edit, re-scored by the extraction evaluation.
