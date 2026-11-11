# ADR-0055: Vault tables for statements

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-11-11

## Context
Brief 05 reads full bank and platform statements. The tracer's vault (`person`, `evidence_item`, `statement_row`) has nowhere to keep a statement's account, period and balances, or to flag a possible duplicate (ADR-0028). R-03 needs an approved ADR for a schema change.

## Decision
- A `statement` table, one row per statement evidence item: person, account title, account number, IBAN, currency, period from and to, and opening and closing balances in minor units.
- `statement_row` gains `balance_minor`, the running balance the statement states, and `possible_duplicate_of`, which points to a stored row that might be the same transaction.
- Tables are still created from the SQLAlchemy metadata. Alembic migrations start with the first local release, when vaults hold data that must survive an upgrade.

## Consequences
Statements reconcile against their own balances before storage. Every new table carries `person_id` (ADR-0035).
