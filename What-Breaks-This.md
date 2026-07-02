# What Breaks This Design

**Scope:** The known limits of the architecture (ADR-000 – ADR-004) — the conditions under which a responsible engineering team would intentionally redesign it. This document identifies where the assumptions behind the current design stop being true. It proposes no changes, solves no problems, and recommends no future technologies; identifying the boundary is the goal, not crossing it.

This is not a failure analysis or a list of operational incidents. Server, network, disk, and database failures are operational events handled by the architecture's durability and recovery properties, not architectural limits.

---

## 1. Purpose

The architecture is deliberately optimized for a specific problem: ~50M events/day `[Observed, brief]`, a two-engineer operating team `[Observed, brief]`, a `<5s` freshness requirement, deterministic identity needs, and a $50K/month ceiling. Its simplicity — a single durable log, managed services, one new datastore, deterministic-only identity — is a direct consequence of those constraints.

Every one of those constraints is an assumption. This document states the conditions under which each stops holding, and therefore the conditions under which a different architecture becomes the correct choice. The limits below are not defects; they are the edges of a design intentionally scoped to its problem.

## 2. Architectural Boundaries

The design rests on assumptions that were stated and labeled when the decisions were made. Each defines a boundary:

- **Volume is modest.** ~578 events/sec average, ~5,800/sec at the stated peak `[Estimated, derived]`. The choice of a single managed log and managed serving stores over a heavier streaming platform follows from this being a reliability problem at modest volume, not a throughput problem.
- **The operating team is small.** Two engineers `[Observed, brief]`. The preference for boring, managed, few systems — and the deliberate limit of one new datastore — follows directly from what two people can operate.
- **Identity is deterministic.** The MVP resolves identity only from explicit first-party signals; probabilistic matching is intentionally excluded.
- **Retention is bounded.** Hot data is assumed to span roughly 30–90 days, cold roughly 13 months `[Assumed]`. The analytical store's sizing and cost fit this window.
- **Freshness tolerates replay.** The `<5s` analytical target is compatible with a replay-oriented, projection-based serving model. The design assumes no consumer requires freshness tighter than what a log-and-projection path can deliver.
- **Compliance scope is GDPR/CCPA and SOC 2** as stated in the brief. The deletion and isolation model is scoped to these.

## 3. Conditions That Would Require Redesign

Each condition below is the point at which one of the boundaries above stops holding. At these points the current design is no longer the correct engineering choice — not because it fails, but because its governing assumption no longer describes the problem.

**Sustained volume far beyond the modest-scale assumption.** If sustained throughput grew by one to two orders of magnitude, the single-log, managed-store, right-sized design would no longer match the problem. The decision to avoid a heavier streaming and processing platform was explicitly conditioned on modest volume; a materially larger, sustained volume is the condition that reopens it.

**Operational ownership beyond a small team.** The design's simplicity is calibrated to two engineers. If the system had to support many teams, many independent tenants' custom logic, or an on-call organization with different boundaries, the "boring, managed, few" principle would be optimizing for the wrong operating model, and a design with stronger internal separation would become appropriate.

**Identity requirements that demand probabilistic resolution.** The MVP is deterministic by deliberate scope. If the product required cross-device or cross-session linkage that first-party signals cannot provide, probabilistic resolution would become a genuine requirement rather than a deferred option. The identity model was designed to *accommodate* this extension, but adopting it is a different operational and correctness commitment than the current design makes.

**Analytical workloads exceeding the datastore's assumptions.** The analytical store was chosen for high-cardinality aggregation and segmentation over a bounded resident window. Workloads outside that shape — for example, far longer hot-resident retention, or query patterns fundamentally unlike aggregation and segmentation — would move the workload outside the assumptions the datastore selection was made under.

**Latency requirements incompatible with replay-oriented serving.** The serving model derives state from a durable log by projection. A requirement for freshness or consistency tighter than a log-and-projection path can provide — beyond the separately-served decisioning path's point-lookup budget — would conflict with the replay-oriented model at the center of the design.

**Compliance requirements beyond those considered.** The deletion, isolation, and retention model is scoped to GDPR/CCPA and SOC 2. Requirements materially beyond these — stricter data-residency guarantees, or erasure semantics the immutable-log-plus-projection model does not naturally support — would press against assumptions the design did not set out to meet.

**Retention requirements beyond the bounded window.** The replay-based migration and recovery model, and the analytical store's sizing, assume a bounded retention window. A requirement to keep the full raw event history hot and replayable indefinitely would change both the cost basis and the recovery model.

## 4. Deliberate Non-Goals

The following were never goals of this architecture. They are absent by choice, not omission, and their absence is not a limit to be corrected within this design:

- **Web-scale throughput.** The design is right-sized to the stated volume, deliberately, per the principle of designing to real numbers rather than hypothetical scale.
- **Probabilistic identity in the MVP.** Excluded by scope; the architecture supports it as a future extension but does not implement it.
- **A general-purpose data platform.** The system serves the stated analytics, personalization, segmentation, and export needs — not an open-ended analytical platform for arbitrary future workloads.
- **Infinite retention.** Bounded retention is assumed; unbounded hot history is a non-goal.
- **Operation by a large organization.** The design is calibrated to a small team; it does not attempt the internal separation a large operating organization would require.

## 5. Closing Statement

This architecture is intentionally bounded. Each limit above is the inverse of an assumption that was stated when the corresponding decision was made — modest volume, a small team, deterministic identity, bounded retention, replay-compatible freshness, and a defined compliance scope. Where those assumptions hold, this is the correct design for the problem. Where they stop holding, a different design becomes correct, and the conditions for that are the ones stated here.

A design with no known limits has not been examined closely enough. The limits of this one are understood, and they are the edges of a deliberate scope — not gaps in an incomplete one.
