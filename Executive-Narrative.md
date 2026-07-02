# Real-Time Analytics Pipeline — Engineering Narrative

This document orients a reviewer to the engineering packet. It states the problem, the single idea the design turns on, how the pieces fit, what was decided and rejected, and where the evidence lives. It does not restate the architecture decision records or strategy documents; it points to them. Read this first, then inspect the artifacts it references.

## 1. Problem

The brief asks for a real-time analytics pipeline to replace a system that loses roughly 3% of events at peak and serves dashboards 15–30 minutes stale `[Observed, brief]`. The workload is about 50M events per day `[Observed, brief]` across 500+ tenants. The requirements are a sub-five-second dashboard freshness target, millisecond personalization lookups, behavioral segmentation, warehouse export, and GDPR/CCPA deletion. The constraints are the part that shapes everything: two engineers to build and operate it, a $50,000/month infrastructure ceiling, and a hard rule that the existing SDK cannot break `[Observed, brief]`.

## 2. Central Thesis

50M events per day is about 578 events per second on average, and roughly 5,800 per second at the stated peak `[Estimated, derived]`. That workload is the premise on which every architectural decision rests. At that rate this is not a big-data problem — it is a reliability and operability problem that a previous design happened to solve badly. The current system does not fail because the volume is enormous; it fails because it loses data under load and cannot be reasoned about. So the design goal is not maximum throughput or maximum flexibility. It is a system two people can operate, that does not lose acknowledged events, and that can be recovered and reasoned about when something goes wrong. Every decision in the packet is a consequence of taking that seriously. Where the design looks conservative, that is deliberate: at this scale, conservatism is correctness.

## 3. Architecture

The five architectural decisions (ADR-000 through ADR-004) form one system built around a single durable, replayable log as the source of truth.

Events enter through a stateless collector that acknowledges a write only after it is durably committed to the log, and fails closed if it cannot. Everything downstream is a projection of that log rather than a second copy of authority. Two serving paths consume the log independently: an analytical path that maintains the sub-five-second dashboard state in a columnar store, and a decisioning path that maintains per-visitor state in an existing key-value store for millisecond personalization lookups. Separating them means the failure or contention of one cannot degrade the other. Identity resolution reads the log and writes only new, immutable correction events on a second logical stream — it never mutates recorded events, which keeps identity reversible, a compliance requirement. Warehouse export is one more independent consumer of the same log.

The single new managed system is the analytical store; everything else is either existing infrastructure or a managed service chosen to keep the operational surface small. The coherence comes from the log: because state is derived from it, the same mechanism gives durability, recovery by replay, and the ability to add a consumer without disturbing the others. See the [architecture diagram](architecture/architecture-diagram.svg).

## 4. Why These Decisions

The reasoning behind the architecture is most visible in what was deliberately rejected.

A heavier streaming and processing platform — the reflexive choice for "real-time analytics" — was not adopted, because it is sized for a throughput problem this workload does not have, and it would enlarge the operational surface beyond what two engineers can carry. A managed log is the right tool at 578 events per second; a self-managed distributed streaming cluster is not. Similarly, the analytical store is a single managed columnar system rather than a general-purpose data platform, because the workload is aggregation and segmentation over a bounded window, not arbitrary analytics. Identity resolution is deterministic-only in the initial scope; probabilistic matching is architecturally supported but deliberately deferred, because adopting it changes the correctness and compliance posture and is a decision that should be made explicitly, not by default.

The through-line is that operability was valued over maximum flexibility, on purpose. Each rejected alternative was more capable in the abstract and worse for this workload and this team. Right-sizing to real numbers, and labeling those numbers, is the governing principle (ADR-000).

## 5. Operational Safety

The packet does not stop at designing the architecture. It specifies how the architecture is introduced, how its correctness is validated before it is trusted, and how failure is handled — because for a system replacing a live pipeline, those are the questions that actually determine success.

The migration strategy moves off the existing system by replaying into the new one and running both in parallel on identical traffic, so the new system is validated against the old before it serves anyone. The validation strategy defines the evidence each guarantee must produce before adoption — including a benchmark for the deletion cost that the analytical-store decision itself flags as its weakest point. The rollback strategy preserves the durable log and the investigation evidence while returning read authority to the existing system, so reverting is a routing decision, not a rebuild. These three documents interlock: validation defines the bar, migration gates on it, rollback triggers when a gate fails after cutover.

## 6. Engineering Boundaries

Two documents define the design's limits rather than its capabilities. One states the conditions under which this architecture would need to be redesigned — sustained volume orders of magnitude larger, identity requirements that demand probabilistic resolution, compliance scope beyond what was considered. The other states which decisions remain human because they carry accountability rather than because automation cannot perform them — cutover approval, rollback initiation, retiring the legacy platform.

They are in the packet on purpose. A design with no stated limits has not been examined closely enough. Naming where the assumptions stop holding is what makes the rest of the design trustworthy: it shows the boundaries were understood when the decisions were made, not discovered afterward.

## 7. Evidence

The submission is built to be inspected, not taken on assertion. Its claims are tied to artifacts a reviewer can open or run.

The central technical claim — that no acknowledged event is lost, even under a durable-boundary outage — is backed by an executable test that measures a naive control against the proposed design under an injected failure and reports whether the durability invariant holds. It fails loudly if the invariant is violated, and it is deterministic and reproducible. The budget claim is backed by the AWS Pricing Calculator's own exported estimate for the six AWS services, plus ClickHouse's published pricing for the analytical store, with a runnable cost model that reproduces the figures; the AWS portion is $855.39/month and the full estimate is approximately $1.5K/month against the $50,000 ceiling `[Calculator-verified for the AWS portion]`. The architecture decisions, strategies, and diagram are themselves inspectable records, and the repository's commit history provides a chronological record of the design's evolution.

The evidence log is the index. It maps each major claim to its strongest supporting artifact and states, plainly, what the packet does not claim: there is no production deployment, no customer data, and no independent verification. Every number carries a source label — Observed, Estimated, Benchmarked, or Assumed — so the basis of each figure is visible rather than implied.

## 8. AI Usage

The packet was produced through a review-board process using three models with separated roles: one as design collaborator, one as the technical writer for the architecture documents after decisions were locked, and one as an independent reviewer whose job was to challenge the important documents rather than write them. The separation was deliberate — agreement between models was never treated as evidence of correctness, and each recommendation was evaluated on its merits. Responsibility for the architecture, the evidence, and every accepted claim remained human. The AI usage disclosure in the repository gives the full account, including the specific cases where review caught wording that would have overstated the available evidence.

## 9. Closing

The architecture is intentionally bounded. It is deliberately sized to the workload the brief describes, it fits well within the budget and the two-engineer constraint, and the evidence demonstrates those claims rather than asserting them. Where its assumptions would stop holding, the packet identifies those limits directly rather than hiding them.

The engineering packet is intentionally complete: the architecture, the reasoning behind it, the evidence supporting it, and the boundaries within which it remains valid are all explicit. The referenced artifacts contain the implementation detail; this narrative is only the guide to them.
