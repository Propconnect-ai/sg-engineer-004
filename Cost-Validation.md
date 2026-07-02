# Cost Validation

**Purpose:** Demonstrate that the proposed architecture (ADR-000 – ADR-004) can operate within the brief's $50,000/month infrastructure ceiling `[Observed, brief]` while remaining practical for a two-engineer team. This is a financial-feasibility validation, not a cost-optimization exercise. It introduces no new architecture and changes no technology.

All AWS figures are taken from the AWS Pricing Calculator (US-East-1) and verified against an exported estimate generated at the time of submission; ClickHouse Cloud figures are taken from ClickHouse's official pricing page. Per-unit rates are labeled **Benchmarked**, and the AWS service totals are **Calculator-verified** against the exported estimate held in the evidence repository. Sizing derives from the locked architecture and the brief's workload; each assumption is labeled Observed, Estimated, or Assumed.

---

## 1. Infrastructure Sizing

**Workload basis:** 50M events/day `[Observed]`; ~578 events/sec average, ~5,800/sec peak `[Estimated, derived]`; ~350-byte events `[Assumed — typical web-behavior event: identifiers ~100 B, type/timestamp ~30 B, URL ~100 B, small custom-properties object ~100 B]`; 500+ tenants `[Observed]`; hot retention ~60 days, cold ~13 months `[Assumed]`.

**Derived data volume:** 50M × 350 B ≈ 17.5 GB/day raw `[Estimated]`. At ~5× columnar compression `[Assumed — conservative; event data commonly compresses 5–10×]`, 60-day hot resident ≈ 210 GB `[Estimated]`; 13-month cold in S3 ≈ 1.4 TB `[Estimated]`.

**Component sizing:**

- **Collector — ECS/Fargate.** 1 service; 2 tasks baseline (multi-AZ availability, not throughput), autoscaling to ~6 at peak; 0.5 vCPU / 1 GB per task `[Estimated]`. Justification: a stateless validate-and-append service is I/O-bound on the durable write, not CPU-bound; 0.5 vCPU is generous at ~578 eps average, and 6 tasks clear ~5,800 eps peak with headroom. Modeled at an average of 3 running tasks.
- **Kinesis Data Streams — on-demand.** `[Assumed — per ADR-001's flagged preference; on-demand removes shard management for a two-engineer team.]` Two logical streams (raw events, identity corrections).
- **Decisioning store — ElastiCache (Redis).** Bounded per-visitor recent state. Memory calculation: at a ~30-minute recent-state window `[Assumed]` and ~10 events/visitor/session `[Assumed]`, active visitor-state ≈ 100K entries, rounded conservatively to ~500K `[Estimated]`; at ~2 KB/entry `[Assumed]` the working set is ~1 GB, ~2–3 GB with overhead. This does **not** justify a 13 GB node; the calculation right-sizes downward. Priced conservatively at `cache.r7g.large` × 2 (primary + replica) — deliberately over-sized rather than under-claimed, so the estimate errs high.
- **Analytical store — ClickHouse Cloud, Scale tier.** `[Assumed — Scale, not Basic: Basic caps storage at 1 TB and is single-zone with no HA, inappropriate for the authoritative customer-facing store. Scale provides 2+ replicas across availability zones.]` ~210 GB hot resident compressed.
- **Application Load Balancer.** 1 ALB fronting the collector `[Assumed]`.
- **S3 — cold tier.** ~1.4 TB and growing `[Estimated]`, S3 Standard `[Assumed]`.
- **CloudWatch.** Service-level structured logging, **not** per-event: ~5 GB/day ≈ 150 GB/month ingested `[Assumed]`. Justification: per-event logging at 50M/day would be a cost trap (hundreds of GB/day); the design explicitly does not do this, consistent with ADR-000 §2 observability being signal-based (buffer depth, consumer lag, DLQ rate), not per-event.
- **Postgres (existing) — OLTP metadata.** Tenant config, identity records, rules. Existing PostgreSQL operational cost, assumed a modest production instance; excluded from architecture decisions because it already exists `[Assumed]`.
- **Data transfer.** Single-region, intra-region `[Assumed — brief requires AWS, no multi-region requirement; keeping one region avoids cross-region transfer entirely]`.

## 2. Pricing (current published rates)

All **Benchmarked**, US-East-1 / ClickHouse Cloud, from the official pricing pages at the time of submission:

- Fargate: $0.04048/vCPU-hour, $0.004445/GB-hour.
- Kinesis on-demand: $0.08/GB data-in, $0.04/GB data-out, $0.04/stream-hour. **Records are billed rounded up to 1 KB** — so ~350-byte events bill as 1 KB, materially increasing data-in volume. This is modeled below rather than glossed.
- ElastiCache `cache.r7g.large` (13 GB): $0.219/node-hour.
- ClickHouse Cloud Scale: $0.2985/compute-unit-hour, $25.30/TB-month storage (confirmed on ClickHouse's official pricing page, Scale tier, us-east-1); a small multi-replica Scale service is approximately $500/month at our footprint.
- ALB: ~$22/month base.
- S3 Standard: ~$0.023/GB-month.
- CloudWatch Logs: $0.50/GB ingested, $0.03/GB-month stored.

## 3. Monthly Cost Table

AWS figures below are the exact monthly costs from the AWS Pricing Calculator estimate (exported, in the evidence repository). ClickHouse and Postgres are outside the AWS calculator and are sourced/labeled separately.

| Service | Configuration | Monthly Cost | Source |
|---------|--------------|--------------|--------|
| Amazon Kinesis Data Streams | On-demand; 2 streams; 578 rec/sec, 1 KB-rounded, 3 consumers, 1-day retention | $318.92 | AWS Calculator-verified |
| AWS Fargate (collector) | 3 tasks × 0.5 vCPU / 1 GB, 24/7 | $54.06 | AWS Calculator-verified |
| Amazon ElastiCache (Redis) | cache.r7g.large × 2, on-demand, 100% util | $319.74 | AWS Calculator-verified † |
| Elastic Load Balancing (ALB) | 1 ALB; EC2/IP targets, ~100 new conn/sec | $39.79 | AWS Calculator-verified |
| Amazon S3 (cold tier) | 1,400 GB S3 Standard | $32.20 | AWS Calculator-verified |
| Amazon CloudWatch | 50 metrics + 150 GB logs ingested, 1-mo retention | $90.68 | AWS Calculator-verified |
| **AWS subtotal** | | **$855.39** | **AWS Pricing Calculator (exported estimate)** |
| ClickHouse Cloud | Scale tier, ~210 GB hot + storage | ~$500 | Benchmarked (official Scale-tier rates) |
| Postgres (existing) | Modest production instance; pre-existing, excluded from architecture decisions | ~$150 | Assumed |
| **Steady-state total** | | **approximately $1.5K/month** | **Calculator-verified (AWS) + Benchmarked (ClickHouse) + Assumed (Postgres)** |

† The exported AWS estimate's ElastiCache config summary also lists unpopulated Serverless and data-tiering sections (a Memcached default and a `cache.r6gd.12xlarge` at zero nodes). These carry no cost; the billed configuration is 2× `cache.r7g.large` Redis on-demand, which the calculator's own calculation panel confirms at $0.219/node-hour.

**Steady-state operation uses approximately 3% of the $50,000/month ceiling** `[Calculator-verified for the AWS portion]` — a margin of more than 30×. The margin is itself a signal: at ~5,800 peak events/sec this is not a scale problem, and a cost near the ceiling would indicate gross over-provisioning, not right-sizing (ADR-000 §4).

## 4. Migration Overlap Cost

The Migration Strategy requires temporary parallel operation: the existing platform stays authoritative while the proposed platform runs alongside it, until validation passes. During that window both stacks bill simultaneously.

- **Legacy infrastructure:** its current run cost, unchanged during overlap `[Assumed — not itemized here; it is the pre-existing bill].`
- **Proposed infrastructure:** approximately $1.5K/month (AWS portion $855.39 calculator-verified).
- **Overlap:** legacy + approximately $1.5K/month for the duration of parallel operation.

Even if the legacy platform's cost were an order of magnitude larger than the proposed platform's, the combined overlap would remain far inside the $50,000 ceiling. The proposed platform's absolute cost is small enough that temporary duplication is not a budget risk. Overlap duration is set by validation, not by schedule (Migration Strategy), so no fixed timeline is asserted; the conclusion holds across any reasonable overlap length because the added cost is approximately $1.5K/month regardless of duration.

## 5. Financial Risk Assessment

- **Event growth beyond estimate.** Cost scales roughly with volume. A 10× sustained increase would move the dominant line items (Kinesis, ClickHouse) into the low thousands/month — still well within budget. Sustained growth of one to two orders of magnitude is the boundary at which the architecture itself is reconsidered (*What Breaks This Design*), not merely the budget.
- **ClickHouse storage growth.** Driven by hot-retention length. If hot retention exceeded the assumed 60 days, resident storage and compute grow proportionally; at $25.30/TB-month storage is cheap, and compute is the larger lever. Managed by TTL-based aging to S3 (ADR-003), keeping hot resident bounded.
- **CloudWatch log growth.** The most common cost surprise. Mitigated by the explicit assumption of service-level, not per-event, logging and by retention policies. Per-event logging is the failure mode and is deliberately excluded.
- **Kinesis 1 KB rounding.** Already modeled: small events bill at 1 KB minimum, roughly tripling data-in volume versus raw bytes. This is included in the $318.92 calculator figure, not discovered later. Client-side aggregation could reduce it but is an optimization, not required for budget fit.
- **Autoscaling during sustained peaks.** Fargate scales with load; sustained peak raises collector cost from tens to low hundreds/month — immaterial against the ceiling.
- **Cross-region traffic.** Avoided by single-region deployment. Would only arise if multi-region were introduced, which is out of scope (*What Breaks This Design*).

Every risk above is either already modeled, cheap to absorb, or bounded by an assumption stated elsewhere in the packet. None threatens budget fit.

## 6. Conclusion

- **Steady-state operation fits inside the budget** with large margin: approximately $1.5K/month (AWS portion $855.39, calculator-verified) against a $50,000 ceiling — roughly 3%.
- **Temporary migration overlap remains acceptable:** the proposed platform adds approximately $1.5K/month during parallel operation, which stays far inside the ceiling regardless of overlap duration or legacy cost.
- **No architectural changes are required** to meet the budget. The design is not merely affordable but substantially under-budget, consistent with its deliberate right-sizing to a modest-scale, reliability-focused problem.

The budget constraint is satisfied with headroom sufficient to absorb significant growth before cost — rather than architecture — becomes the binding concern.

The AWS Pricing Calculator exported estimate (PDF, all six services, $855.39/month total), the AWS calculator screenshots, the ClickHouse Cloud official pricing screenshots, and the runnable `cost_model.py` are included in the evidence repository. Together they provide both vendor-generated pricing evidence (Tier 1) and an inspectable calculation source record (Tier 3), so the budget claim is reproducible rather than asserted.
