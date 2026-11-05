# ADR-0042: PyYAML for registry files; psycopg 3 as the Postgres driver

- Status: Approved
- Approved by: Muhammad Jariruddin, 2026-10-30

## Context
ADR-0040 makes registry entries YAML files, and ADR-0014 chooses Postgres, but neither names the library that reads YAML or the driver SQLAlchemy uses to reach Postgres. R-02 needs an approved ADR for each.

## Decision
PyYAML (safe loader only) for registry files, with `types-PyYAML` for mypy. psycopg 3 (binary wheels) as SQLAlchemy's Postgres driver.

## Consequences
Both are mature and widely used. No other YAML or Postgres library may be added (R-04).
