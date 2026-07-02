# ADR-003: Analytical Datastore Selection

**Status:** Accepted · **Date:** 2026-07-01 · **Constrained by:** ADR-000 (all) · **Implements:** ADR-002 analytical path
---

## Requirements (evaluation framework)

- **R1 — Query patterns.** <5s-fresh high-cardinality aggregations (counts, distinct-visitor, funnels) over time windows, filtered by tenant + arbitrary attributes; behavioral segmentation ("did X ≥N times in window W" — group-by-then-filter-on-aggregate). Append-heavy, read-aggregate — not OLTP, no point lookups, no multi-row transactional updates.
- **R2 — Freshness.** Queryable <5s from ingestion `[Observed]`; continuous streaming ingestion, not batch loads.
- **R3 — Retention & scale.** ~30–90d resident `[Assumed; A7]` ≈ 1.5B–5B events `[Estimated, derived]`; clean aging-out to cold; performant at multi-billion-row scale.
- **R4 — Multi-tenancy.** Isolate query + ideally performance across 500+ tenants `[Observed]` without 500 separate databases.
- **R5 — Operational fit (hard gate, ADR-000 §3).** Managed, no self-hosted cluster ops, operable by two engineers.
- **R6 — Compliance deletion.** Targeted single-visitor event deletion for GDPR/CCPA `[Observed]` with bounded, viable cost.

---

## Candidate evaluation

(Exotic OLAP engines — Druid/Pinot — excluded: they fail R5 harder than ClickHouse and add capability we don't need at this volume. Naming only to reject would be padding.)

**Candidate 1 — PostgreSQL (owned), tuned rollups.** R1 ⚠️ weak (row-store; ad-hoc segmentation on arbitrary attributes is its worst case — can't pre-aggregate every segment) · R2 ✅ · R3 ⚠️ weak (multi-billion resident rows strain single Postgres; plausibly the current bottleneck) · R4 ✅ · R5 ✅✅ strongest (owned, RDS/Aurora) · R6 ✅✅ strongest (native row DELETE). Wins operability + compliance; weak exactly where the core workload lives.

**Candidate 2 — Managed columnar OLAP (ClickHouse Cloud, representative).** R1 ✅✅ strongest (columnar; ad-hoc segmentation over billions is core use) · R2 ✅ (streaming, seconds-fresh) · R3 ✅✅ (built for the volume; native TTL aging) · R4 ✅ (tenant-keyed partitions; isolation at 500+ needs care, not heroics) · R5 ✅ managed (one new system, no cluster ops) · R6 ⚠️ weak spot (columnar deletes heavier than OLTP; mechanisms exist — see below). Wins the core workload; deletion is its weakness.

**Candidate 3 — Amazon Redshift.** R1 ✅ · R2 ❌ near-disqualifying (warehouse-class, batch-oriented; <5s live freshness fights its design) · R3 ✅ · R4 ✅ · R5 ✅ · R6 ⚠️ (columnar delete cost). Right tool for the customer warehouse export target — a different problem in this system — not for <5s live serving.

---

## Decision

Managed columnar OLAP (ClickHouse Cloud class) is the strongest overall fit for the analytical serving layer given the stated requirements and constraints.

The requirements drive this. R1 (ad-hoc high-cardinality segmentation) and R3 (multi-billion resident scale) are the core of the workload, and they place Postgres at a clear disadvantage — arbitrary behavioral segmentation over billions of rows is what a row-store handles worst, since you cannot pre-compute every possible segment. R2 (<5s freshness) places Redshift at a clear disadvantage, its batch orientation fighting live-serving freshness. Among the candidates, the managed columnar OLAP store is the one that fits R1 + R2 + R3 + R5 well together, which is what the serving path actually demands.

Postgres is repositioned, not discarded. It remains the right store for OLTP-shaped data — tenant config, identity records, personalization rules — the relational, transactional, deletion-friendly metadata. Each engine serves its shape; we don't force one to do both, and we don't replace Postgres.

---

## Exception to ADR-000 §3 (explicit)

ADR-000 §3 directs us to prefer boring, managed services the team already operates and to minimize distinct systems. Adding ClickHouse is the first deliberate exception to that principle in this design, so we justify it explicitly rather than slipping it in:

- **Why the exception is warranted:** the analytical workload (R1/R3) is precisely what our owned store (Postgres) is architecturally worst at. Forcing it onto Postgres risks re-importing the current system's bottleneck — i.e. reusing owned tech here would undermine the very reliability/operability goals §3 exists to serve. The principle's intent (operable, low-risk systems) is better served by the exception than by literal compliance.
- **Why it stays within §3's spirit:** we choose a managed OLAP service (no cluster ops — the §5 hard gate holds), add exactly one new system, and confine the exception to the one workload that needs it. We do not open the door to a proliferation of new tech; this is a single, bounded, justified addition.
- **The cost we accept:** one new system for the team to learn, and a harder deletion story (R6). Both are bounded and named.

This is the model for any future §3 exception: name it, justify it against the principle's intent, bound it.

---

## Trade-offs (accepted)

- **One new managed system to learn (ClickHouse).** Bounded, one-time, no ops burden.
- **Harder GDPR deletion than a row-store (R6).** ClickHouse provides mechanisms to support row-level deletion (mutations / ALTER … DELETE, TTL, partition-scoped operations), but their operational cost and performance under real GDPR erasure workloads require validation before production. We are not asserting the cost is sufficiently bounded — we are asserting viable mechanisms exist and that proving their cost at 500-tenant scale is a pre-production gate. (This is the weakest joint.)
- **Consistency between ClickHouse (analytics) and Postgres (metadata).** Accepted — the log is source of truth; neither store is authoritative for the other's data.

---

## Weakest joint (flagged per policy)

R6 deletion under real GDPR load is unvalidated, and it's the most likely thing to be worse than scored. ClickHouse's deletion mechanisms are real and used in production, so this isn't a fabricated escape — but I have not proven their cost/performance when erasure requests are frequent and deletes contend with live ingestion and query at 500-tenant scale. If that contention proves severe, R6 could reopen this decision under criterion #2 (compliance failure). Mitigation path: validate with a real deletion benchmark before commit — a strong candidate for our operating artifact. Until validated, this remains an open, labeled risk, not a solved problem.

---

## Assumptions (Register)

A8 — analytical QPS across 500 tenants unquantified `[Assumed]`. A9 — segmentation interactive, not heavy batch `[Assumed]`. A10 — GDPR erasure frequency low enough that bounded columnar deletes don't overwhelm the store `[Assumed — ties to weakest joint]`.
