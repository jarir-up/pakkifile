# Rules — PakkiFile

A second model checks every pull request's diff against these rules, and the merge is blocked on any violation. That CI gate is disabled while the project runs on zero spend; `/code-review` against this file before every commit stands in (see `docs/PROGRESS.md`).

How to keep this file useful:
- If a linter, formatter or type checker can enforce a rule, configure the tool and leave the rule out of this file.
- Each rule must be checkable by reading a diff. "Write good code" is not a rule.
- Rule IDs never change or get reused. Retire a rule by marking it `(retired)`.
- To accept a violation on purpose, the owner adds `waive R-07: <reason>` to the PR description.

## Must never

- **R-01** Commit secrets, keys, tokens or credentials, including in tests, fixtures and comments.
- **R-02** Add a new dependency unless an approved ADR in `docs/adr/` covers it.
- **R-03** Change a public API, database schema or stored data format unless an approved ADR covers it.
- **R-04** Add a second way of doing something the codebase already does one way. Migrate the old way completely, or don't add the new one.
- **R-05** Swallow errors: no empty catch blocks, and no catch-alls that hide the failure from the caller or the logs.
- **R-06** Add code that guards against an unlikely or purely hypothetical race condition or security edge case without a linked owner approval in the PR description.
- **R-07** Add taglines, helper text or secondary labels to the UI.

## Must always

- **R-10** A behavior change comes with tests that would fail without it.
- **R-11** A bug fix comes with a regression test.
- **R-12** New code goes where the folder map in ARCHITECTURE.md says, and respects its module boundaries.
- **R-13** UI uses the tokens and components in DESIGN.md, not hard-coded colors, sizes or one-off components.

## Project rules

- **R-20** Never let a language model produce, compute or alter a figure. Every number shown to a user comes from a function in `figures`.
- **R-21** Every requirement record carries its source document, section, URL, retrieval date and last-verified date.
- **R-22** Code in `registry`, `sources` or the checklist site build never reads, stores, logs or transmits applicant documents or figures.
- **R-23** No user-facing text states or implies approval or refusal odds, or suggests hiding, altering or working around a fact.
- **R-24** Money is integer minor units plus a currency code, with `Decimal` and the project rounding mode for arithmetic. No floats for money.
- **R-25** Untrusted text (applicant documents, fetched pages, community stories) reaches a prompt only as delimited data, never inside instructions.
- **R-26** Only the evaluation harness reads frozen test or adversarial data.
- **R-27** Applicant data reaches a language model only through the redaction function in `llm`.
- **R-28** Synthetic data is labelled synthetic in its file name or a field.
- **R-29** Evidence items are never modified. Annotations and exports are new files.
