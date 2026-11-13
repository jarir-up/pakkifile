# ADR-0059: A held-out layout is a template change of a bank already read

- Status: Proposed

## Context
ADR-0029 says the dev and test splits differ in layouts. With deterministic parsers, a layout no parser knows simply fails, which says nothing about how well the vault works. Banks do change their statement templates, and that is worth testing (owner, 2026-11-13).

## Decision
Amends ADR-0029's layout rule only. The test split's held-out layout is a template change of a bank the vault already reads, such as an older Meezan statement layout: the same fields, moved or relabelled. Templates and instances still differ as ADR-0029 says.

## Consequences
A held-out layout tests whether a parser survives a bank's redesign. When one fails, its fix is a parser change, and the test split is then regenerated (ADR-0029).
