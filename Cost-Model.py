#!/usr/bin/env python3
"""
Source Record (Evidence Log E12)

Reproduces the steady-state monthly cost estimate used in the Cost Validation document.

Inputs:
- workload assumptions (labeled Observed / Estimated / Assumed in the doc)
- benchmarked vendor pricing (official AWS / ClickHouse pricing pages)

Outputs:
- monthly infrastructure estimate

This model is intentionally simple and intended for auditability rather than
production forecasting.

The AWS per-service figures below are the authoritative values produced by the
AWS Pricing Calculator (exported estimate held in the evidence repository); this
script does not re-derive them from scratch, because the calculator is the
authoritative source and re-derivation only reintroduces rounding disagreements.
For each AWS line the sizing that produced it is shown in a comment so the input
is auditable. ClickHouse Cloud (not in the AWS calculator) is computed here from
its published per-unit Scale-tier rates. Prices may change; re-verify against the
official pricing pages before relying on absolute figures.
"""

# ---- AWS services: authoritative figures from the AWS Pricing Calculator export ----
# (US-East-1; see evidence repository for the exported PDF and screenshots)
AWS = {
    # service: (monthly_usd, sizing_note)
    "Fargate (collector)":          (54.06,  "3 tasks x 0.5 vCPU / 1 GB, 24/7"),
    "Kinesis (on-demand, 2 streams)":(318.92, "578 rec/sec, 1 KB-rounded, 3 consumers, 1-day retention"),
    "ElastiCache (Redis, 2 nodes)": (319.74, "cache.r7g.large x2, on-demand, 100% util"),
    "ALB":                          (39.79,  "1 ALB, EC2/IP targets, ~100 new conn/sec"),
    "S3 (cold)":                    (32.20,  "1,400 GB S3 Standard"),
    "CloudWatch":                   (90.67,  "50 metrics + 150 GB logs ingested, 1-mo retention"),
}

# ---- ClickHouse Cloud Scale tier: computed from published per-unit rates ----
# (official pricing page, us-east-1; see evidence repository screenshots)
CH_STORAGE_TB_MO = 25.30    # $/TB-month (Scale)
CH_HOT_TB        = 0.210    # [Estimated] compressed hot resident (~210 GB)
CH_COMPUTE_FLOOR = 499.00   # small multi-replica Scale service, published example (~$500)
def clickhouse():
    return CH_COMPUTE_FLOOR + CH_HOT_TB * CH_STORAGE_TB_MO

# ---- Postgres: existing infrastructure, assumed (not an architecture decision) ----
PG_MONTH = 150.00           # [Assumed] modest existing production instance

def main():
    aws_total = 0.0
    for name, (cost, note) in AWS.items():
        print(f"{name:38s} ${cost:8.2f}   # {note}")
        aws_total += cost
    print(f"{'AWS subtotal (calculator-verified)':38s} ${aws_total:8.2f}")

    ch = clickhouse()
    print(f"{'ClickHouse Cloud (Scale, computed)':38s} ${ch:8.2f}   # {CH_HOT_TB*1000:.0f} GB @ ${CH_STORAGE_TB_MO}/TB + ~${CH_COMPUTE_FLOOR:.0f} compute")
    print(f"{'Postgres (existing, assumed)':38s} ${PG_MONTH:8.2f}")

    total = aws_total + ch + PG_MONTH
    print(f"{'STEADY-STATE TOTAL':38s} ${total:8.2f}")
    print(f"{'% of $50,000 ceiling':38s} {total/50000*100:8.1f}%")

if __name__ == "__main__":
    main()
