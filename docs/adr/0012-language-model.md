# ADR-0012: Language model: local via Ollama by default; hosted models optional and off

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-10-30

## Context
IncomeLens ADR-005 chose a local model via Ollama for the MVP. The project runs on zero spend: no paid APIs anywhere.

## Decision
A local model served by Ollama is the default for all language-model work: requirement extraction, ambiguous-row classification and drafting. A hosted model is optional, enabled only by explicit configuration, and off by default. Drafts are written with placeholders for figures and names (for example `{{figure:total_income_12m}}`, `{{name:sponsor}}`), and local code fills them in, so no model sees the applicant's figures or names. Model IDs and the provider live in configuration.

## Consequences
Nothing costs money to run, and applicant text stays on the machine by default. Extraction quality depends on what a local model can do; the extraction evaluation (brief 03) shows whether it is good enough. CI must not depend on a paid model. ADR-0017 (numbers rule) holds by construction for drafts. Matches IncomeLens ADR-005's local-first choice, without its later move to a hosted model.
