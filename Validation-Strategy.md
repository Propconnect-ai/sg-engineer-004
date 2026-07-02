# Validation Strategy

**Scope:** The evidence required before the proposed platform is considered correct for production adoption. This document defines *what must be proven and to what standard* — not how to test it. It introduces no new architecture, infrastructure, or tooling, and does not repeat the cutover procedure defined in the Migration Strategy. Where a validation concern is not defined by a locked ADR, it is marked **out of scope**.

This is not a QA test plan. It is the acceptance standard the platform is measured against.

---

## 1. Objective

Establish the evidence that must exist before the proposed platform replaces the existing one. The platform is considered correct when each subsystem — ingestion, serving, identity, replay, and migration equivalence — has produced measured evidence meeting the acceptance criteria in §4, not when it has merely been built.

The standard is correctness, not completeness: it is better to have strong evidence for the guarantees the platform actually makes than broad, shallow coverage. Every acceptance criterion below maps to a guarantee already made by the architecture; nothing here validates behavior the platform does not claim.

Validation precedes adoption. No subsystem is trusted in production on the basis of design review alone; each requires evidence from its own behavior under real or replayed load.

## 2. Validation Principles

1. **Evidence over assertion.** A guarantee is validated only by observed or measured behavior, not by inspection of the design.
2. **Correctness over completeness.** Validate the guarantees the platform makes, deeply, before broadening coverage. Unclaimed behavior is not in scope.
3. **Failure is a first-class test.** Each subsystem is validated under its failure mode, not only its happy path. A guarantee that holds only on clean input is unvalidated.
4. **Peak is the required regime.** Where a guarantee concerns behavior under load, it is validated at peak, because peak is where the current system fails and therefore the only regime that tests the claim.
5. **Reproducibility.** Validation evidence must be reproducible — the same conditions produce the same result — so that a disputed result can be re-examined rather than re-argued.

## 3. Validation Categories

Each category states the guarantee under test and the evidence that satisfies it. Tooling, frameworks, and monitoring systems that produce the evidence are **out of scope** — no locked ADR selects them.

**Ingestion.**
Guarantee: every acknowledged event is durably recorded exactly once; under a durable-boundary outage the collector rejects (retryably) rather than acknowledges-and-loses.
Evidence: a controlled test that drives ingestion through a durable-boundary outage and reconciles, for every acknowledged event, exactly one durable record — with loss and duplication both measured, not assumed. The operating artifact provides this evidence for the acknowledgment contract under a deterministic failure model; validation of the same contract against the production durable log is required before adoption.

**Serving — analytical path.**
Guarantee: freshness within `<5s` and correct aggregation/segmentation results.
Evidence: measured freshness (event-to-queryable latency) at peak load, and result correctness established through the equivalence comparison against the existing system (procedure defined in the Migration Strategy; this document requires only that the comparison meet the acceptance criteria in §4).

**Serving — decisioning path.**
Guarantee: per-visitor state served within its latency budget in the render path.
Evidence: measured lookup latency under load. The specific numeric latency budget is not fixed by a locked ADR and is **out of scope** to define here; validation requires that the measured latency meet whatever budget the team sets for render-path decisioning, at peak.

**Identity.**
Guarantee: deterministic canonical resolution is correct and reversible; corrections re-resolve without mutating raw events.
Evidence: a demonstrated deterministic stitch that correctly re-attributes prior events to a canonical identity, and a demonstrated unmerge that reverses it — with raw events unchanged before and after. Probabilistic matching is out of MVP scope and is not validated.

**Replay / recoverability.**
Guarantee: any projection can be rebuilt from the log and reproduce the same state.
Evidence: a projection dropped and rebuilt by replay, producing state identical to the pre-drop state. This validates recovery as a real operation rather than a design property.

**Migration equivalence.**
Guarantee: the proposed system is at least as complete and correct as the existing one on identical traffic.
Evidence: the parallel-operation comparison defined in the Migration Strategy. This document does not repeat that procedure; it requires that the comparison's results meet the acceptance criteria below.

## 4. Acceptance Criteria

The platform is accepted for production adoption when **all** hold:

1. **Ingestion** — no acknowledged event is lost or duplicated under the tested outage; the exactly-once acknowledgment contract is validated against the production durable log, not only the deterministic model.
2. **Analytical freshness** — measured event-to-queryable latency meets `<5s` at peak load.
3. **Analytical correctness** — aggregation and segmentation results agree with the existing system within explained tolerance, sustained across at least one peak period; the proposed system is expected to be *more* complete at peak, and any other difference is explained, not averaged away.
4. **Decisioning latency** — measured render-path lookup latency meets the team-defined budget at peak.
5. **Identity correctness and reversibility** — a deterministic stitch and its reversal are both demonstrated, with raw events unchanged.
6. **Recoverability** — a projection rebuilt by replay reproduces identical state.
7. **Deletion impact** — a representative GDPR/CCPA deletion benchmark has been executed against the analytical datastore under representative production load, demonstrating that deletion processing neither breaches the `<5s` analytical freshness objective nor disrupts ingestion. This validates the mitigation for the deletion-cost risk identified in ADR-003 as the architecture's weakest joint.
8. **Reproducibility** — each of the above is reproducible under stated conditions.

Numeric thresholds not fixed by a locked ADR (decisioning latency budget; tolerance bands for equivalence) are set by the team from real validation data and are **out of scope** to fix in advance. Fixing them here would present an assumption as a requirement.

## 5. Failure Handling

Validation exists to stop a wrong system from reaching production. When a criterion is not met:

- **The criterion blocks adoption.** No subsystem advances to production authority on a failed or unexplained criterion. This is the default; there is no override on the basis of schedule.
- **An unexplained difference is treated as a real defect, not noise.** In equivalence comparison, a discrepancy is either a proposed-system bug or an existing-system loss. Which it is must be established before the criterion can pass; "close enough" is not a resolution.
- **A failed guarantee reopens its decision, not just its test.** If ingestion cannot validate the exactly-once contract against the production log, that is an architectural failure surfaced by validation, not a test to be relaxed — it is escalated to the relevant decision, consistent with the project's reopening criteria.
- **The existing system remains the fallback throughout validation.** Because validation occurs before and during parallel operation while the existing system is still authoritative, a failed criterion has no customer impact — it delays adoption, it does not cause an outage.

The response to failed validation is to fix the system or revisit the decision, never to weaken the criterion.

## 6. Completion Criteria

Validation is complete — the platform is correct for production adoption — when:

1. Every acceptance criterion in §4 is met with reproducible evidence.
2. Each guarantee has been validated under its failure mode, not only its happy path.
3. Load-dependent guarantees have been validated at peak.
4. Any criterion that failed and was addressed has been re-validated, not waived.

Completion is a statement about evidence, not effort: the platform is correct when the evidence exists, regardless of how long it took to produce.

## 7. Assumptions

- **Real or replayed load is available for validation.** Peak-regime validation requires either a natural peak during the validation window or a representative load; the mechanism for producing load is **out of scope**.
- **The existing system provides a valid comparison baseline.** Equivalence validation assumes the existing system's output is a usable reference despite its known ~3% peak loss `[Observed, brief]`; the comparison accounts for that loss by expecting the proposed system to be more complete, not identical, at peak.
- **Team-defined thresholds exist by validation time.** Criteria with no ADR-fixed threshold (decisioning latency; equivalence tolerance) require the team to set values before validation concludes; setting them is out of scope for this document.

**Explicitly out of scope** (no locked ADR decides these; not invented here): test frameworks, monitoring and alerting systems, load-generation tooling, numeric SLO values not fixed by an ADR, and the procedures already defined in the Migration Strategy. These are execution decisions for the implementing team.
