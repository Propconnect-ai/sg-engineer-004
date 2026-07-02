# Migration Strategy

**Scope:** How the existing analytics pipeline transitions to the proposed architecture. This document covers the *transition*, not how the target architecture works. It introduces no new architecture, infrastructure, or tooling. Where a decision has not been made by a locked ADR, it is marked **out of scope** rather than invented here.

---

## 1. Objective

Move from the current system — synchronous-appearing ingestion with ~3% event loss at peak and 15–30 minute latency `[Observed, brief]` — to the proposed architecture without losing events, without breaking existing customer integrations, and without a high-risk single cutover.

The migration is treated as a correctness exercise rather than a scheduling exercise. The existing system remains authoritative for customer-facing analytics until the proposed system has been validated against it. Success is measured by validated equivalence before cutover rather than migration speed.

The durable event log and replay-based recovery let the proposed system be introduced alongside the existing platform without migrating historical state.

## 2. Guiding Principles

1. **Correctness over speed.** Each stage advances on evidence, not schedule. A delayed migration is acceptable; a lossy one is not.
2. **Replay, not data migration.** The new system is populated by consuming the live event stream from a known point forward, and rebuilt by replaying the log. Historical backfill beyond the log's retention window is **out of scope**; pre-log history remains queryable in the existing system during parallel operation.
3. **Parallel operation before replacement.** Both systems consume the same traffic long enough to validate equivalence under real load, including at least one peak period.
4. **Validation before cutover.** Customer-facing traffic moves only when measured agreement meets the cutover criteria (§5).
5. **Reversible at every stage.** The existing system runs unchanged throughout parallel operation, so reverting is returning reads to it — not a rebuild.
6. **Customer-facing continuity.** Ingestion, personalization, and dashboards must not degrade during migration.

## 3. Migration Phases

Phases are gated: each completes only when its exit condition is met, and each describes *what must be true*, not the deployment mechanism. **Deployment tooling, routing, and traffic-splitting mechanics are out of scope** — no locked ADR selects them.

**Phase 0 — Prerequisite validation (blocking).**
- **SDK retry behavior must be verified before any traffic reaches the new collector.** The proposed collector fails closed under a durable-boundary outage; if the existing SDK does not retry transient (5xx) responses, rejected events become lost and the ingestion strategy must be revisited. This blocks the migration.
- Confirm the new collector accepts the existing SDK payload unchanged. No SDK change is permitted.

Exit: both confirmed, or the design is revisited.

**Phase 1 — Shadow ingestion (existing system authoritative).**
The proposed ingestion path observes the same live traffic as the existing pipeline. The proposed system builds its projections from the log but serves nothing to customers. The mechanism for delivering the same traffic to both systems is **out of scope**; this document requires only that both observe the same events over the same period.

Exit: proposed projections populate from the log and can be dropped and rebuilt by replay without discrepancy.

**Phase 2 — Parallel validation (existing system still authoritative).**
Both systems run on identical live traffic and are compared (§4). This phase must span at least one peak-load period, since peak is the regime the current system fails in and therefore the only regime where the new system's core claim is tested.

Exit: cutover criteria (§5) met and sustained across the required window, including peak.

**Phase 3 — Cutover (proposed system becomes the authoritative system).**
Customer-facing reads move to the proposed system. The existing system continues running — not yet decommissioned — as the reversion target. The routing mechanism is **out of scope**.

Exit: proposed system becomes the authoritative system; existing system idle-but-available; no regression against the completion criteria (§6) over the stabilization window.

**Phase 4 — Decommission (existing system retired).**
The existing pipeline is retired only after the completion criteria hold for the full stabilization window. Until then it is retained as the reversion target.

Exit: existing system decommissioned; the proposed system is the sole authoritative platform.

## 4. Parallel Operation

Parallel operation is both the migration mechanism and the accuracy-validation mechanism. Both systems process identical live traffic; their outputs are compared over the same event population and window to validate correctness before cutover, satisfying the brief's data-accuracy requirement.

Three comparisons:

- **Ingestion completeness.** Event counts admitted by the proposed collector vs. the existing pipeline over identical windows. Events the old system dropped at peak are, in the new system, either durably recorded or explicitly rejected-and-retried. Divergence is the primary signal.
- **Analytical agreement.** Aggregate and segmentation results compared per window and tenant. A difference is either a new-system bug or an old-system loss; which it is must be established, not averaged away.
- **Identity resolution agreement.** Canonical identity assignments compared for consistency. Disagreement is reproducible and traceable to a specific event or assertion.

Reconciliation tolerates known, explained differences — notably, the proposed system is expected to show *more* complete data at peak. An unexplained difference blocks cutover. Specific metrics, thresholds, and comparison cadence are set by the team from Phase 2 data; this document fixes the principle (measured equivalence, peak included), not thresholds, which cannot be responsibly set before observing real parallel data.

## 5. Cutover Criteria

Cutover (Phase 2 → 3) proceeds only when **all** hold:

1. **SDK retry verified** (Phase 0) — the zero-loss guarantee is satisfiable end-to-end.
2. **Ingestion completeness validated** — no acknowledged events lost, and any gap versus the existing system is explained (and generally favors the new system) across the validation window.
3. **Analytical and identity agreement** within explained tolerance, sustained, including across at least one peak-load period.
4. **Freshness SLA met** — the analytical path serves within `<5s` and the decisioning path within its latency budget under real load, at peak.
5. **Recoverability demonstrated** — a projection has been rebuilt by replay and reproduced the same state.
6. **Reversion path confirmed available** — the existing system can resume authority for customer-facing reads.

If any criterion regresses after being met, cutover does not proceed. Thresholds for criteria 2–4 are set from Phase 2 data and are out of scope to fix in advance.

## 6. Completion Criteria

Migration is complete (Phase 4 may proceed) only when, with the proposed system authoritative:

1. All cutover criteria continue to hold through the stabilization window.
2. At least one peak-load period has been served by the proposed system as authoritative with no regression in loss, freshness, or accuracy.
3. GDPR/CCPA deletion has been exercised end-to-end for a real erasure request. Deletion cost at scale is a flagged open risk validated before production adoption; completion requires that erasure works correctly and that its cost has been measured rather than assumed.
4. The reversion path is no longer needed — the team has decided the proposed system is stable enough to retire the existing one. **This decision stays human** and is the point of no return.

## 7. Assumptions

- **SDK retry (blocking).** The zero-loss guarantee depends on the existing SDK retrying transient failures; verified in Phase 0.
- **Retention.** The log's retention window bounds what can be rebuilt by replay. Pre-log history remains in the existing system during parallel operation; backfill beyond retention is out of scope.
- **Parallel traffic delivery.** Both systems can observe the same live traffic during parallel operation. The mechanism is out of scope.
- **Peak within the validation window.** Validation requires observing at least one peak; if none occurs naturally, the window extends until one does.
- **Deletion cost.** GDPR deletion is exercised for correctness at completion; its cost at scale is validated separately.

**Explicitly out of scope** (no locked ADR decides these; not invented here): deployment tooling, traffic-routing and read-switching, parallel-traffic duplication, load generation for forced peaks, and numeric validation thresholds. These are execution decisions for the implementing team.
