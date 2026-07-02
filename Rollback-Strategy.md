# Rollback Strategy

**Scope:** How the system safely returns to the existing platform if validation or early production operation indicates the proposed platform should not remain authoritative. This document defines the principles and operational sequence of rollback. It introduces no new architecture, infrastructure, or tooling, and does not repeat the Migration or Validation Strategies. Where a rollback concern is not defined by a locked ADR, it is marked **out of scope**.

This is not a disaster recovery plan, a deployment guide, or an implementation runbook.

---

## 1. Objective

Return customer-facing analytics to the existing platform, without data loss and without discarding the evidence needed to understand why, if the proposed platform should not remain authoritative.

Rollback is possible and inexpensive because of a property established in the Migration Strategy: the existing system remains authoritative and unchanged through parallel operation, and only cutover (Phase 3) moves customer-facing reads to the proposed platform. Before decommission, the existing system is a running, current fallback — not an archive to be restored. Rollback is therefore the act of returning reads to it, not the act of rebuilding state.

Rollback is an operational safety mechanism, not an engineering failure. Its availability is a designed property of the migration sequence; exercising it is a correct response to evidence, not an error.

## 2. Rollback Principles

1. **Customer correctness over deployment progress.** If the proposed platform's correctness is in doubt, reads return to the existing system. Adoption progress is never preserved at the cost of serving customers incorrect data.
2. **Rollback is evidence-driven, not schedule-driven.** Rollback is initiated on observed conditions (§3), never deferred to protect a timeline and never forced to meet one.
3. **Preserve durable data.** The durable log and its recorded events are never discarded on rollback. Rollback changes which system serves reads; it does not delete recorded data.
4. **Preserve replayability.** Because projections are rebuilt from the log, preserving the log preserves the ability to reconstruct the proposed platform for a later attempt. Rollback must not compromise this.
5. **Preserve investigation evidence.** The state that led to rollback — the proposed platform's projections, the divergence that triggered it, the durable log at that point — is retained for root-cause analysis, not cleared to return to a clean slate.
6. **The existing system remains authoritative until decommission.** Until the Migration Strategy's completion criteria are met and the existing system is retired, it is the fallback and rollback is available.

## 3. Rollback Triggers

Rollback is initiated when evidence indicates the proposed platform should not remain authoritative. The conditions are drawn from the acceptance guarantees the platform is required to meet; this document references those guarantees rather than restating them.

- **A validation acceptance criterion fails after cutover.** Any guarantee validated before cutover (the ingestion durability guarantee, analytical freshness and correctness, decisioning latency, identity correctness and reversibility, recoverability, deletion impact) that is subsequently observed to fail in production is a rollback condition.
- **An unexplained correctness divergence in production.** A discrepancy between expected and served results that cannot be immediately explained is treated as a correctness failure, consistent with the Validation Strategy's stance that unexplained differences are defects, not noise.
- **A customer-facing regression** in ingestion completeness, freshness, personalization, or dashboards attributable to the proposed platform.

The threshold and detection mechanism for these conditions are **out of scope** — no locked ADR defines monitoring or alerting. This document defines *what constitutes a rollback condition*, not how it is observed. The decision to initiate rollback on an observed condition **stays human** (§7).

## 4. Rollback Procedure

Rollback reverses cutover: it returns customer-facing reads to the existing system. It does not reverse ingestion, and it does not restore state.

1. **Return customer-facing reads to the existing system.** The existing system resumes authority for dashboards, personalization, and analytics. The mechanism for moving reads is the same routing concern the Migration Strategy marks out of scope; it is **out of scope** here for the same reason.
2. **Leave ingestion to the durable log running.** Ingestion is not rolled back. The collector and durable log continue to record events, so no data is lost during or after rollback and the log remains continuous across the rollback boundary. This is what preserves replayability.
3. **Retain the proposed platform's projections in place.** Projections are not torn down. They are retained as investigation evidence (§5) and as the basis for a future attempt.
4. **Confirm the existing system is serving correctly.** Rollback is complete only when the existing system is confirmed authoritative and serving customers correctly (§6) — not at the moment reads are redirected.

Because the existing system was never modified and continued running through parallel operation, this sequence returns the system to a known-good serving state without reconstruction.

## 5. Data Preservation

The distinction between what is and is not rolled back is the core of this strategy.

**Preserved (never discarded on rollback):**
- **The durable log and all recorded events.** Ingestion continues; the log is continuous across rollback. Preserving it preserves both the record of what happened and the ability to rebuild the proposed platform later.
- **The proposed platform's projections at the point of rollback.** Retained as the primary evidence for root-cause analysis — the divergence that triggered rollback is examined against the state that produced it.
- **The existing system's data.** Unaffected throughout, as it remained authoritative and unmodified.

**Rolled back:**
- **Only the serving authority** — which system answers customer-facing reads. Nothing else.

**Deliberately not done:**
- **No deletion of proposed-platform state to "return to clean."** Clearing evidence to reset would destroy the information needed to fix the cause and would forfeit the replay basis for a second attempt.
- **No mutation of the durable log.** Consistent with the immutable-log model, rollback appends and preserves; it never rewrites recorded events.

This preservation is what allows a subsequent migration attempt: with the log intact and the failure understood, the proposed platform can be corrected and re-validated without re-migrating historical state.

## 6. Rollback Completion Criteria

Rollback is complete when **all** hold:

1. The existing system is authoritative for all customer-facing reads and confirmed serving correctly.
2. Ingestion to the durable log is confirmed continuous — no events lost across the rollback boundary.
3. The proposed platform's projections and the triggering divergence are retained and available for analysis.
4. The condition that triggered rollback has been documented and preserved for root-cause analysis.

Rollback returns the platform to the pre-cutover posture of the Migration Strategy: the existing system authoritative, the proposed platform running in parallel but not serving customers, and the durable log intact — a state from which another migration attempt is possible once the cause is addressed.

## 7. Assumptions

- **The existing system is available as a fallback.** Rollback assumes the existing system has not been decommissioned. After decommission (Migration Strategy Phase 4), rollback as defined here no longer applies; that point is deliberately the migration's point of no return.
- **Read authority can be returned to the existing system.** The mechanism is the same routing concern marked out of scope in the Migration Strategy.
- **The rollback decision is made by a person.** Initiating rollback on an observed condition is a human decision, not an automated one, given its customer-facing consequence.

**Explicitly out of scope** (no locked ADR decides these; not invented here): monitoring and alerting, the read-routing mechanism, detection thresholds for rollback conditions, and any procedure already defined in the Migration or Validation Strategies. These are execution decisions for the implementing team.
