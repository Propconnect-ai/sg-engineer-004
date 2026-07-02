# ADR-002: Serving-Layer Split — One Path or Two

**Status:** Locked ✅ · **Date:** 2026-07-01 · **Constrained by:** ADR-000 §2, §5 · **Consumes:** ADR-001 log

---

## Decision

The system exposes two independent serving paths, not one, because the two consumer needs it must satisfy have fundamentally different access patterns and latency SLAs that no single store serves well. Both paths are independent consumers of the ADR-001 log; they share the log and nothing else.

---

## Scope boundary

This ADR establishes the existence of a dedicated decisioning path and its access pattern (low-latency per-visitor point lookup). It does not solve how per-visitor behavioral state is maintained — the state model, windowing, identity association, and store mechanics are deferred to a later ADR. Readers should not infer that behavioral-state management is solved here; only that a separate path for it is architecturally required.

---

## The two paths

| | Analytical path | Decisioning path |
|---|---|---|
| **Question** | "What is happening across my visitors?" | "What should I show this visitor now?" |
| **Access pattern** | Fan-in — aggregate/scan across many events and tenants | Point lookup — one visitor's recent state by key |
| **Latency SLA** | <5s freshness `[Observed, brief]` | Single-digit–tens of ms, page-render hot path `[Assumed — weakest joint, below]` |
| **Consumers** | Dashboards, behavioral segmentation, warehouse export | Real-time personalization triggers |
| **Store shape implied** | Analytical (columnar/aggregation-oriented) | Low-latency key-value |

The architectural claim (this is the whole decision): the dashboard requirement is a freshness-bounded aggregation problem; the personalization requirement is a low-latency point-lookup problem. A store optimized for fast aggregations over many events is the wrong shape for a per-visitor render-path lookup, and vice versa. Collapsing them into one serving path forces one store to do both jobs and it does at least one of them badly — most commonly, the personalization SLA silently fails because an aggregation-shaped store can't answer a point lookup in render-path time. Therefore the paths are separated at the architecture level, before any technology is chosen.

Why two paths is safe operationally (not just correct): because both are independent log consumers (ADR-001 §2, §3), one can fail, lag, or be rebuilt-by-replay without affecting the other. The split reduces blast radius rather than adding coupling — a failure in dashboard aggregation cannot degrade personalization, and neither is a source of truth (the log is). Under contention, ADR-000 §5 governs: customer-facing reads are prioritized, and among them we rank paths in the relevant ADR.

---

## Options considered

- **Single unified serving path (one store for both).** For: fewer components (ADR-000 §3); one thing to operate. Rejected: no single store shape serves both a <5s cross-event aggregation and a millisecond per-visitor point lookup well; the unified store fails at least one SLA. The operability saving is illusory — you pay it back in query-tuning gymnastics forcing one engine to fake the other's access pattern.
- **Two paths, shared store, different query layers.** For: one datastore, two access APIs. Rejected: still one physical store's performance envelope; a spike in analytical scans contends with point lookups, coupling the two SLAs through shared resources — violates the isolation that's the entire point.
- **Two independent paths, separate stores (recommended).** Accepts more than one store in exchange for SLA isolation and correct tool-per-job.

**Recommendation:** Two independent serving paths, each an independent consumer of the log, each free to use a store shaped for its access pattern. Technology selection for the analytical path is deferred to ADR-003; the decisioning store is uncontested (Redis, already owned) and will be formalized alongside its state mechanism in the deferred behavioral-state ADR.

---

## Trade-offs (accepted)

- **More than one serving store to operate.** Accepted: they're isolated consumers, so operational blast radius shrinks even as component count rises — a rare case where "more parts" improves operability rather than harming it. This is the deliberate exception to ADR-000 §3, justified by SLA isolation.
- **Two paths can diverge in freshness.** Accepted: neither is source of truth; divergence is a lag/replay concern (ADR-001 §3), not a correctness one.

---

## Weakest joint (flagged per policy)

The decisioning path's millisecond SLA is assumed, not observed. The brief says "trigger personalization based on recent behavior" but never numbers the latency. The two-path split is most justified if personalization fires synchronously in the page-render path (millisecond budget). If personalization is actually asynchronous (update a segment / fire a webhook within seconds), the decisioning path's latency need relaxes toward the analytical path's, and the split becomes weaker justified — possibly collapsible. Defense: render-path personalization is the dominant pattern for a "personalization platform," so the assumption is reasonable; it is labeled explicitly, and if personalization proves async, this decision should be revisited under reopening-criteria #1/#3. This is the single assumption most likely to be challenged in a walkthrough, and we carry it labeled rather than hidden.

---

## Assumptions

Personalization is synchronous to page render `[Assumed — weakest joint; Register A5]`. The two paths' consumers tolerate independent freshness, no cross-path transactional consistency required `[Assumed; Register A6]`.

---

## Risks & detection

Freshness lag on either path under 10x spike — detect via per-consumer lag (ADR-000 §2); resolve via ADR-000 §5 prioritization. Deeper per-store risks belong to the implementing ADRs.

---

## One-line summary (for citation)

One durable log, two independent serving paths — analytical (<5s aggregation) and decisioning (ms point-lookup) — as separate log consumers with isolated failure domains. Establishes the decisioning path's existence; defers its state mechanism.
