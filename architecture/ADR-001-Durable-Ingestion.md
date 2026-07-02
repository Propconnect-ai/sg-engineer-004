# ADR-001: Durable Ingestion — Acknowledgment Boundary & Buffering

**Status:** Locked ✅ · **Date:** 2026-07-01 · **Constrained by:** ADR-000 §1, §2, §3

---

## Decision

Ingestion is built around a single invariant: the collector does not acknowledge an event to the SDK until that event has crossed a durable persistence boundary. The durable boundary is a managed, replayable streaming log (Kinesis Data Streams as the intended implementation), and the collector's sole responsibility is validate-then-durably-append. Processing is a separate concern that consumes the log independently.

### Architectural guarantees

- **Acknowledgment follows durability, never precedes it.** A 2xx to the SDK means "this event is durably recorded and will not be lost," not "received." On failure to reach the durable boundary, the collector returns a retryable error so the SDK's retry behavior recovers the event.
- **Ingestion is decoupled from downstream processing.** A slow or failed consumer (dashboard aggregation, personalization, export) cannot exert backpressure onto ingestion, because they share only the durable log, not a synchronous call path. This is the direct fix for the observed spike-crash symptom.
- **Replay and recovery are first-class.** Because the boundary is a log with retention, any consumer can be rebuilt or caught up by re-reading from a known offset. Recovery = replay, not restore-from-backup.
- **Backpressure behavior is explicit (fail-closed).** If the durable boundary is unavailable or throttling, the collector fails closed — it returns a retryable error rather than acknowledging and buffering in volatile memory. We never trade durability for availability at the front door: a rejected-and-retried event is recoverable; an acknowledged-and-lost event is not.
- **Operational simplicity for two engineers.** The collector is stateless (state lives in the log), so it scales horizontally with no failover complexity. The managed log removes cluster operations.

---

## On the current system (honest framing)

One plausible explanation consistent with the observed symptoms is synchronous coupling between ingestion and downstream processing. Regardless of the exact implementation, introducing a durable ingestion buffer and an ack-after-durability boundary isolates ingestion from downstream failures and closes the acknowledged-but-lost gap. `[Assumed root cause — stated as hypothesis, not fact.]`

---

## Options considered (rejected)

- **SQS (queue, not log)** — no native replay/fan-out; rebuilding them on top inverts its operability advantage.
- **Self-managed Kafka / MSK** — operational weight two engineers cannot carry at ~5,800 peak eps `[Estimated, derived]`; over-engineering the brief is designed to detect (ADR-000 §3).
- **"Faster Postgres" / synchronous with replicas** — doesn't address coupling; a faster downstream still crashes ingestion when a spike outruns it.

---

## Trade-offs (accepted)

- **Higher tail latency at the front door.** Ack-after-durability is slower than fire-and-forget. Accepted: the SDK call is async to page render `[Assumed]`, so added ingest latency doesn't affect the visitor's experience, and it buys the durability guarantee. Correctness over speed at this boundary.
- **Fail-closed sheds load under a durable-boundary outage.** During a rare managed-service outage we return retryable errors rather than accept events we can't guarantee. We favor durability/consistency over ingest availability — deliberately, because the brief names zero data loss as an explicit requirement and states no ingest-availability SLA.

---

## Risks & detection

- **SDK retry behavior is a migration validation checkpoint, not an architectural assumption.** The architecture must not depend on undocumented client behavior. Production rollout is gated on verifying that the existing SDK correctly retries transient retryable failures. If that validation fails, the ingestion strategy must be revisited, because the zero-data-loss guarantee cannot be satisfied without client participation. `[Migration gate — owned by the migration ADR.]`
- **Producer-side gap is the true durability frontier.** Even with ack-after-durability, an event lost in the network before reaching the collector, or a collector crash mid-request, is unrecoverable. This is the irreducible edge — and the natural target for the operating artifact to measure. `[Flagged for the deferred artifact decision.]`
- **Partition-key skew (hot shard from a large tenant)** — flagged for a later ADR; detection via per-shard iterator-age.

---

## Assumptions

SDK transport is async to page render `[Assumed]`. At least three independent log consumers exist `[Assumed, inferred from stated features]`.

---

## One-line summary (for citation by later ADRs)

Ingestion is a stateless collector enforcing ack-after-durable-commit against a managed replayable log (Kinesis), decoupled from all downstream processing, failing closed under durable-boundary outage. Durability chosen over ingest-availability, deliberately. SDK retry behavior is a migration gate, not an assumption.
