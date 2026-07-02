# Real-Time Analytics Pipeline — Engineering Submission

A production-oriented system design for replacing a real-time analytics pipeline that loses events during traffic spikes and serves stale dashboards. The proposal is intentionally constrained to a two-engineer operating model and a $50,000/month infrastructure budget. Rather than optimizing for hypothetical hyperscale, the design focuses on correctness, durability, operability, and explicit engineering trade-offs.

This repository contains the architecture decisions, migration and validation strategies, operating boundaries, executable evidence, and supporting analysis used to justify the proposed design.

---

## How to review this repository

If you have 30–45 minutes, read in this order:

1. **`executive-narrative.md`** — Recommended starting point. Explains the problem, the governing thesis, and how the repository is organized.
2. **`architecture/`** — The five ADRs and architecture diagram. This is the design itself.
3. **`validation-strategy.md`** — The strongest single indicator of how the design establishes correctness before production.
4. **`evidence/`** — Review the executable durability artifact if you want to verify the central engineering claim rather than simply read about it.

If you have less time, the Executive Narrative provides sufficient context before exploring the individual ADRs.

---

## Repository structure

### Core architecture

**`executive-narrative.md`**

Orientation document for reviewers. Introduces the problem, the governing architectural thesis, and the reasoning behind the overall design.

**`architecture/`**

Five Architecture Decision Records (ADR-000 through ADR-004) together with the architecture diagram.

- `ADR-000` — Architecture Principles
- `ADR-001` — Durable Ingestion
- `ADR-002` — Serving Layer Split
- `ADR-003` — Analytical Datastore
- `ADR-004` — Identity Resolution

**`architecture/architecture-diagram.svg`**

Complete architecture overview showing ingestion, durable log, serving projections, identity resolution, and downstream consumers.

### Strategy documents

These documents explain how the architecture is introduced and operated safely.

- `migration-strategy.md`
- `validation-strategy.md`
- `rollback-strategy.md`

Together they describe migration sequencing, validation gates, and rollback criteria.

### Engineering boundaries

These documents explicitly define the limits of the design.

- `what-breaks-this.md`
- `what-stays-human.md`

Rather than pretending the architecture solves every problem, they document where redesign becomes necessary and which decisions intentionally remain under human ownership.

### Supporting documentation

**`evidence-log.md`**

Maps each major architectural claim to the strongest supporting evidence and identifies what the submission does not claim.

**`cost-validation.md`**

Demonstrates that the proposed architecture operates comfortably within the stated monthly infrastructure budget.

**`ai-usage-disclosure.md`**

Explains how AI tools were used during preparation while identifying the architectural decisions and engineering judgment that remained the author's responsibility.

### Evidence

**`evidence/`**

Contains the executable operating artifact supporting ADR-001.

Current contents include:

- `adr001_durability_invariant.py`

### Cost model

**`cost-model.py`**

Executable Python cost model used to estimate monthly infrastructure costs under the stated workload assumptions and validate compliance with the $50,000/month operating constraint.

---

## Submission characteristics

- Architecture constrained by explicit operational limits rather than hypothetical scale.
- Every significant assumption is labeled.
- Trade-offs are documented rather than hidden.
- Weakest joints are explicitly identified.
- Recovery and operational behavior are treated as first-class design concerns.
- Central engineering claims are backed by inspectable artifacts wherever practical.

---

## Notes

This repository is an engineering design submission rather than a production implementation.

The Executive Narrative is the recommended entry point.

The ADRs record the permanent architectural decisions, while the remaining documents provide the validation, migration, operational guidance, governance boundaries, and supporting evidence behind those decisions.
