# 04: Figure computed by SQL with row links

**What to build:** the synthetic statement loads into Postgres and a `figures` function returns the largest unattributed credit, its share of total credits, and the rows it came from.

**Blocked by:** 01. Needs ADR-0042.

**Status:** done

- [x] Figure equals the generator's fact table
- [x] Money is integer minor units with a currency code
- [x] The figure carries its source row IDs
