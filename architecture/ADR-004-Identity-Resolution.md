# ADR-004: Canonical Identity — Ownership & Resolution

**Status:** Locked ✅ · **Date:** 2026-07-01 · **Budget tier:** HIGH (irreversible; upstream of behavioral state, segmentation, and R6 deletion) · **Constrained by:** ADR-000 (all), ADR-001 (log = source of truth), ADR-002 (feeds both serving paths)

---

## The question

Not "how do we store identity" but **which component owns the assertion that two identifiers are the same person, and how does a correction to that assertion propagate to everything that consumed it** — without violating our source-of-truth, path-isolation, or contention principles.

---

## Identity model (established)

A visitor is a single persistent identity that accumulates events across time and across the anonymous→known boundary. Identity is an **assertion, not a fact**: we decide two identifiers are the same person, on evidence, and we must be able to undo that decision. The model is **late-bound** (raw events keep their as-observed identifiers; canonical identity is resolved over the identifier graph, not stamped at ingest), **assertion-based**, **graph-structured** (one person = a cluster of linked identifiers), and **reversible**.

Three identifier kinds: **anonymous ID** (default, cheap, untrustworthy — cookie/device), **known ID** (stable, customer-provided — the identity we care about), and **the stitch** (the asserted link between them).

---

## Decision

**A dedicated Identity Resolution Service owns canonical identity as a derived, re-runnable resolution over the identifier graph — but it is not the source of truth for events.** Three ownership boundaries:

1. **The log (ADR-001) owns raw events with their as-observed identifiers.** Immutable; never changes, including on unmerge. This is what makes reversibility possible — corrections re-resolve, they never rewrite history.
2. **The Identity Resolution Service owns the identity graph and the canonical resolution.** System of record for *assertions* ("anon-A links to known-B, on evidence E, at time T") and for the current resolution of each identifier cluster. It owns the *mapping* identifier→canonical identity, not the events.
3. **Downstream consumers own their own materialized view of identity**, treating canonical identity as externally-owned, re-derivable input — never a permanently baked-in fact.

---

## Decision (MVP scope)

**Canonical identity resolution is limited to deterministic, first-party stitching for the MVP.** Assertions are created only from strong explicit first-party signals: authenticated login, verified/authenticated form submission, explicit customer-provided identity binding on an active session.

**Probabilistic identity resolution** (cross-device inference from shared device/IP/timing) is **intentionally excluded from the MVP.** The architecture supports it — the evidence-strength tier and graph model accommodate it as a future extension — but operating a probabilistic matching engine is not justified for two engineers on a three-month MVP (ADR-000 §3, §4). We prefer a correct, operable, narrow identity model over a broad, error-prone one we cannot safely run.

**What is NOT cut (stated to prevent a compliance gap):** the model remains **assertion-based, re-resolvable, and reversible.** Even deterministic stitches can be wrong (shared-device logins fusing two people), and GDPR/CCPA erasure requires deleting a single person — so unmerge/remerge and the immutable-events + derived-resolution separation are retained in full. We cut the weak-evidence tier and inference engine, **not** the correction machinery. Merging without reversibility would create a compliance hole; we do not do that.

---

## Identity lifecycle

- **Observed** — an identifier appears on an event; enters the graph as a node. No claim yet beyond existence.
- **Asserted** — a stitch links two identifiers with an evidence basis; the graph records the edge and its evidence strength.
- **Resolved** — the service computes canonical identity per cluster over the current graph. This is the value downstream reads.
- **Corrected (unmerge/remerge)** — a prior assertion is invalidated or added; the affected cluster is re-resolved. The correction is itself an append-only assertion, so correction history is auditable.

Resolution is a pure function of (immutable events + current assertion set) — replayable, consistent with ADR-001 §3 recovery. The lifecycle is re-entrant: an identifier can be re-resolved any number of times as evidence changes.

---

## Evidence strength

Assertions carry a strength tier so corrections know what to override:

- **Deterministic (strong)** — explicit first-party signal (login, form submit on same session). The MVP's only active tier.
- **Probabilistic (weak)** — inference from correlated signals. Deferred (post-MVP), but the tier is retained in the model.

Rule: **strong overrides weak; weak never overrides strong.** In the MVP only the deterministic tier is active, but the ranking mechanism is retained so probabilistic assertions can be added later without redesign, and so "strong overrides weak" already governs their future interaction with existing links.

**Governance stance:** deterministic stitches auto-apply. Future low-confidence probabilistic merges affecting compliance-sensitive operations should not be applied autonomously — flagged for "what stays human."

---

## Downstream propagation

**Identity is propagated as a re-playable correction, not a distributed transaction.** When resolution changes for a set of identifiers, the Identity Resolution Service emits an identity-correction event to the log (or a dedicated identity-changes stream). Each downstream consumer subscribes and re-attributes its own materialized state for the affected identifiers, at its own pace, using its own store's mechanics.

Why this respects every prior ADR:

- **ADR-001 (log = source of truth):** corrections are replayable events; raw events are never mutated; no consumer is authoritative for identity.
- **ADR-002 (path isolation):** each path consumes corrections independently and re-attributes asynchronously; no synchronous cross-store transaction.
- **ADR-000 §2 (recoverable):** resolution is a pure function of events + assertions, so any consumer's identity view rebuilds by replaying both streams — an identity bug is recoverable, not catastrophic.
- **ADR-000 §5 (contention):** if mass re-resolution floods corrections, the decisioning (customer-facing) path is prioritized; bulk re-attribution of analytical/export is deferred.

**Eventual, not immediate, identity consistency is accepted.** After a correction the two serving paths are briefly out of sync on who-is-who. Accepted deliberately: the brief requires no cross-path transactional identity consistency `[Assumed; A6/A12]`, and synchronous identity updates across all stores would reintroduce the coupling ADR-002 exists to prevent.

---

## System of record, plainly

- **Events:** the log (ADR-001).
- **Identity assertions + canonical resolution:** the Identity Resolution Service.
- **No single "identity column" is authoritative elsewhere** — every downstream identity value is a re-derivable cached projection.

---

## Trade-offs (accepted)

- **Late-bound identity means historical re-attribution.** A stitch retroactively changes what past events belong to; consumers must support re-attributing materialized aggregates. Accepted — it's the only model that survives anon→known; early-binding is simply wrong (the stitch arrives after the events).
- **Eventual identity consistency across paths.** Accepted per above.
- **A new stateful service to own.** Accepted; see weakest joint.

---

## Weakest joint

The identity graph is stateful, correctness-critical, and correction-heavy, and owning it strains ADR-000 §3 — there is no managed off-the-shelf equivalent fitting martech stitching semantics, so we own its correctness and re-resolution performance. The MVP scope cut (deterministic-only) substantially reduces this risk by removing the inference engine and the probabilistic graph, which were the main operational hazard. Residual risk: re-resolution performance under a large deterministic bad-merge rollback is unvalidated. *Defense:* resolution is bounded and replayable (recovery risk mitigated), and the identity graph can largely be implemented using the existing managed PostgreSQL deployment rather than new tech (§3 mitigated). Remains a labeled open risk with a validation path, not a solved problem.

---

## Assumptions (Register)

- **A11′** — deterministic-only identity is sufficient for the MVP's customer use cases (real-time personalization + segmentation) without material cross-device gaps `[Assumed]`. Probabilistic matching reclassified from open assumption to explicit deferred scope.
- **A12** — no cross-path transactional identity consistency required `[Assumed; extends A6]`.
- **A13** — re-attribution of historical aggregates on correction is acceptable within freshness SLAs `[Assumed]`.
- **A14** — even deterministic stitches can incorrectly merge distinct people (shared device); reversibility is retained as a compliance requirement, not a probabilistic feature `[Design commitment, not assumption — recorded for rationale]`.

---

## One-line summary (for citation)

Identity is a derived, re-resolvable, reversible assertion over immutable events, owned by a dedicated Identity Resolution Service (system of record for assertions, not events); corrections propagate as replayable events each serving path applies independently. MVP is deterministic-first-party stitching only; probabilistic matching is architecturally supported but deliberately deferred; reversibility is retained regardless.
