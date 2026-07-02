# ADR-000: Architecture Principles

**Status:** Accepted · **Date:** 2026-07-01 · **Context:** Foundational. All subsequent ADRs are constrained by and cite these principles.

---

## Context

We are rebuilding a martech analytics pipeline that ingests ~50M events/day `[Observed, brief]` — ~578 events/sec average, ~5,800/sec at the stated 10x peak `[Estimated, derived]` — operated by two senior engineers `[Observed, brief]` under a $50K/month ceiling `[Observed, brief]`. The current system fails on latency, crashes under spikes, and loses ~3% of events at peak `[Observed, brief]`. These are symptoms of operational fragility, not of insufficient throughput. The following principles exist to keep every downstream decision anchored to operability by a small team rather than to scale we do not have.

---

## Principles

1. **Failure is the default case.** Every component is designed from the question "what happens when this fails?" — not as an afterthought. *Test:* an ADR that cannot state its component's failure and recovery behavior is incomplete.

2. **Predictable, observable, recoverable.** These are measurable commitments, not adjectives.
   - **Predictable:** the system degrades (backpressure, buffering) rather than crashing.
   - **Observable:** every component exposes the specific signal an on-call engineer watches (e.g. buffer depth, consumer lag, DLQ rate).
   - **Recoverable:** state can be rebuilt by replay to a stated RPO.

   *Test:* each ADR names the mechanism for whichever of these it touches.

3. **Prefer boring, managed, and few.** Prefer managed AWS services the team already operates (Postgres, Redis, AWS-native) over self-hosted or novel systems, and minimize the count of distinct systems. A new moving part must justify its operability cost, not merely a performance benefit. *Test:* "can two engineers operate this at 2am without prior deep expertise?" If no, it needs exceptional justification.

4. **Right-size to real numbers, labeled.** Design to ~5,800 peak eps `[Estimated, derived]` with stated headroom, not to hypothetical web scale. Every number carries a source tag: observed / estimated / benchmarked / assumed. *Test:* an unlabeled number is a defect.

5. **Customer-facing workloads win contention.** Under resource pressure, SDK ingestion, personalization decisioning, and dashboard reads take priority over exports, backfills, and historical processing. *Test:* any shared-resource design states which side is shed first.

---

## Consequences

These principles bias us away from throughput-maximizing architectures (Kafka+Flink+Druid) and toward durable-buffer-plus-managed-services simplicity. We accept that this design would need rework above roughly 10–20x current volume `[Assumed]` — a trade we make deliberately, because designing for volume we don't have would violate principles 3 and 4. This is our single most important bet, and if the reviewer's hidden context is "assume 50x growth in 12 months," it's the assumption that would flip the design.
