# ADR-0056: Where row classifications are kept

- Status: Approved (owner, 2026-11-11)

## Context
Rules classify statement rows (ADR-0018). Ambiguous rows go to a local model (ADR-0051), and uncertain ones to the applicant's review (ADR-0052), whose corrections become evaluation data. R-03 needs an approved ADR for the schema.

## Decision
- `statement_row` gains `row_class` (null while unclassified), `class_source` (`rule`, `model` or `applicant`), `class_confidence` (the model's, 0 to 1, null for rules and the applicant) and `needs_review` (true until the applicant decides).
- A `row_correction` table records each review decision: person, row, the class proposed and by which source, the class the applicant chose, and when. It is the evaluation data ADR-0018 asks for, and it never leaves the machine (ADR-0002).
- Rules run at ingestion. The model and review run afterwards, so a statement can be stored without Ollama running.

## Consequences
An applicant's decision always wins over rules and the model. Re-running the rules never overwrites a row the applicant has decided.
