#!/usr/bin/env python3
"""
Operating Artifact - ADR-001 Durability Invariant Test
======================================================

INVARIANT UNDER TEST:
    "For every acknowledged (2xx) event, there exists exactly one durable record."

This is a correctness test, not a demonstration script. It runs two collector
implementations that differ by a SINGLE architectural decision -- the order of
acknowledgment relative to the durable write -- against an IDENTICAL event set,
IDENTICAL failure injection, and the SAME verifier.

    BASELINE  collector: acknowledges, THEN attempts the durable write.
    PROPOSED  collector: durably writes, THEN acknowledges (ADR-001).

Under an injected outage of the durable boundary, the BASELINE collector
acknowledges events it never durably records -> the invariant is VIOLATED.
This reproduces the acknowledged-before-durable FAILURE MODE described in the
brief; it does NOT reproduce the production system, and the loss MAGNITUDE in
this run is a property of the injected scenario, not a claim about the brief's
observed 3%. The PROPOSED collector refuses (5xx) events it cannot durably
record -> those
events are rejected-and-recoverable, never acknowledged-and-lost, so the
invariant HOLDS.

The verifier FAILS LOUDLY (non-zero exit) if the invariant is violated for
either run. A reviewer can edit a collector, rerun, and immediately see
whether the invariant still holds. That is what makes this artifact falsifiable.

Deterministic: same inputs -> same output, every run. No concurrency, no clock,
no randomness, no network, no external dependencies (stdlib only).

Usage:  python3 durability_invariant.py
Runtime: well under 2 seconds on a normal laptop.

NOTE ON NUMBERS: the event count and outage window below are a deterministic
simulation [Simulated], chosen to make the invariant easy to verify -- NOT a
claim about production throughput. The artifact proves the *contract*, not the
infrastructure.
"""

import sys

# ---------------------------------------------------------------------------
# Scenario parameters  [Simulated - chosen for verifiability, not realism]
# ---------------------------------------------------------------------------
TOTAL_EVENTS   = 100          # deterministic, fixed event set
OUTAGE_START   = 40           # durable boundary fails at this event index...
OUTAGE_END     = 60           # ...and recovers at this index (exclusive)
MALFORMED_IDS  = {17, 83}     # events that must be rejected as bad input (4xx)


# ---------------------------------------------------------------------------
# The durable boundary.
# A stand-in for the managed durable log (Kinesis in production). The only
# properties that matter for the invariant: (1) a successful write produces
# exactly one persisted record; (2) during an outage, writes fail explicitly
# rather than silently succeeding. `up` models availability; we flip it to
# inject the outage. Records are keyed so we can detect BOTH loss (0 records)
# and duplication (>=2 records) -- the "exactly one" half of the invariant.
# ---------------------------------------------------------------------------
class DurableBoundary:
    def __init__(self):
        self.records = {}   # event_id -> count of durable records
        self.up = True

    def write(self, event_id):
        """Attempt a durable write. Raises if the boundary is down.
        A raise means NOTHING was persisted (no partial/silent write)."""
        if not self.up:
            raise IOError("durable boundary unavailable")
        self.records[event_id] = self.records.get(event_id, 0) + 1

    def record_count(self, event_id):
        return self.records.get(event_id, 0)


# ---------------------------------------------------------------------------
# Response codes (HTTP-like), so the contract reads plainly.
#   2xx  acknowledged  -> caller (SDK) considers the event delivered
#   4xx  rejected      -> bad input, never retried, never our durability concern
#   5xx  rejected      -> transient failure; SDK retries (recoverable, not lost)
# ---------------------------------------------------------------------------
ACK_2XX     = 200
REJECT_4XX  = 400
REJECT_5XX  = 503


def validate(event):
    """Shared input validation. Malformed events are rejected by BOTH
    collectors -- proving the artifact handles bad input, not just the
    happy path."""
    return event["id"] not in MALFORMED_IDS


# ===========================================================================
# THE ONLY MEANINGFUL VARIABLE: order of ack vs. durable write.
# The two functions are otherwise identical. This diff IS the architecture.
# ===========================================================================

def control_collect(event, boundary):
    """BASELINE: acknowledge first, then try to persist.
    The client considers the event delivered the moment it receives 200 -- but
    the durable write can still fail afterwards, leaving an acknowledged event
    with zero durable records. Ack-before-durable."""
    if not validate(event):
        return REJECT_4XX
    ack = ACK_2XX                      # <-- acknowledged HERE, before durability
    try:
        boundary.write(event["id"])
    except IOError:
        pass                           # write lost; but we already acked
    return ack


def proposed_collect(event, boundary):
    """PROPOSED (ADR-001): persist first, acknowledge only on durable success.
    If the durable boundary is down we return 5xx (retryable) and do NOT
    acknowledge. The event is refused, not lost. Ack-after-durable."""
    if not validate(event):
        return REJECT_4XX
    try:
        boundary.write(event["id"])    # <-- durability FIRST
    except IOError:
        return REJECT_5XX              # refuse; never ack what we can't persist
    return ACK_2XX                     # acknowledged only after durable success


# ---------------------------------------------------------------------------
# The scenario driver. Identical for both collectors: same events, same
# outage window, same order. The collector is the only thing that changes.
# ---------------------------------------------------------------------------
def run_scenario(collector):
    boundary = DurableBoundary()
    events = [{"id": i} for i in range(TOTAL_EVENTS)]
    outcomes = {}   # event_id -> response code

    for i, event in enumerate(events):
        # Inject the durable-boundary outage for a fixed window.
        boundary.up = not (OUTAGE_START <= i < OUTAGE_END)
        outcomes[event["id"]] = collector(event, boundary)

    return boundary, outcomes


# ---------------------------------------------------------------------------
# THE VERIFIER -- the heart of the artifact.
# Checks the invariant for one run and returns (passed, stats). Every
# acknowledged (2xx) event must have EXACTLY ONE durable record. Zero = loss.
# Two+ = duplication. Either breaks the invariant.
# ---------------------------------------------------------------------------
def verify(boundary, outcomes):
    acked      = [eid for eid, code in outcomes.items() if code == ACK_2XX]
    rejected5xx = sum(1 for c in outcomes.values() if c == REJECT_5XX)
    rejected4xx = sum(1 for c in outcomes.values() if c == REJECT_4XX)

    lost, duplicated, exactly_once = [], [], 0
    for eid in acked:
        n = boundary.record_count(eid)
        if n == 0:
            lost.append(eid)
        elif n == 1:
            exactly_once += 1
        else:
            duplicated.append(eid)

    passed = (len(lost) == 0 and len(duplicated) == 0)
    stats = {
        "acked": len(acked),
        "exactly_once": exactly_once,
        "lost": len(lost),
        "duplicated": len(duplicated),
        "rejected_5xx_recoverable": rejected5xx,
        "rejected_4xx_bad_input": rejected4xx,
    }
    return passed, stats


def report(name, description, passed, stats):
    print(f"  {name}  ({description})")
    print(f"    acknowledged (2xx)................. {stats['acked']}")
    print(f"    -> with exactly one durable record. {stats['exactly_once']}")
    print(f"    -> LOST (acked, 0 records)......... {stats['lost']}")
    print(f"    -> DUPLICATED (acked, >=2 records). {stats['duplicated']}")
    print(f"    rejected 5xx (retry-recoverable)... {stats['rejected_5xx_recoverable']}")
    print(f"    rejected 4xx (bad input).......... {stats['rejected_4xx_bad_input']}")
    verdict = "INVARIANT HOLDS" if passed else "INVARIANT VIOLATED"
    print(f"    VERDICT: {verdict}")
    print()


def main():
    print("=" * 70)
    print("ADR-001 CORRECTNESS TEST")
    print("=" * 70)
    print()
    print("INVARIANT UNDER TEST")
    print()
    print("    For every acknowledged (2xx) event,")
    print("    there exists exactly one durable record.")
    print()
    print("=" * 70)
    print(f"Scenario [Simulated]: {TOTAL_EVENTS} events; durable boundary "
          f"down for events [{OUTAGE_START},{OUTAGE_END}); "
          f"{len(MALFORMED_IDS)} malformed.")
    print("=" * 70)
    print()

    # Identical scenario, two collectors.
    control_boundary, control_outcomes = run_scenario(control_collect)
    proposed_boundary,  proposed_outcomes  = run_scenario(proposed_collect)

    control_passed, control_stats = verify(control_boundary, control_outcomes)
    proposed_passed,  proposed_stats  = verify(proposed_boundary,  proposed_outcomes)

    report("BASELINE [ack-before-durable]",
           "reproduces the acknowledged-before-durable failure mode from the brief",
           control_passed, control_stats)
    report("PROPOSED [ADR-001: ack-after-durable]",
           "the ADR-001 durability contract",
           proposed_passed, proposed_stats)

    # ---------------------------------------------------------------------
    # Falsifiable pass/fail. This is a correctness test:
    #   - The PROPOSED design MUST satisfy the invariant. If it does not, the
    #     artifact FAILS -- our design claim is wrong and must be fixed.
    #   - The CONTROL MUST violate the invariant. If it does not, the
    #     experiment is not actually stressing the contract (the control is
    #     supposed to fail), so the result is not evidence -- also a FAIL.
    # ---------------------------------------------------------------------
    print("=" * 70)
    print("Evidence:")
    print()
    print("  The baseline and proposed implementations were executed against")
    print("  the same deterministic event set, identical failure injection, and")
    print("  the same verifier. The ordering of acknowledgment relative to")
    print("  durable persistence is the only architectural variable.")
    print("=" * 70)
    ok = True
    if not proposed_passed:
        print("FAILED: PROPOSED design violated the durability invariant.")
        ok = False
    if control_passed:
        print("FAILED: BASELINE did NOT violate the invariant -- the")
        print("        scenario is not stressing the contract; result is not")
        print("        valid evidence.")
        ok = False

    if ok:
        print("RESULT: PASSED")
        print()
        print("Invariant satisfied:")
        print()
        print("  \u2713 Every acknowledged (2xx) event")
        print("    has exactly one durable record.")
        print()
        print("Architectural consequence:")
        print()
        print("  Ack-before-durable")
        print("      -> acknowledged-but-lost events are possible.")
        print()
        print("  Ack-after-durable")
        print("      -> eliminates acknowledged-but-lost events")
        print("         under the tested failure model.")
        print("      -> transient failures become retryable rejections instead.")
    else:
        print("RESULT: FAILED")
        print()
        print("Invariant NOT satisfied:")
        print()
        print("  \u2717 An acknowledged (2xx) event")
        print("    had zero or multiple durable records.")
    print("=" * 70)
    print()
    print("Scope: this artifact validates the correctness of the ADR-001")
    print("acknowledgment contract under a deterministic failure model. It is")
    print("not intended to benchmark throughput or to validate managed-service")
    print("durability guarantees.")
    print("=" * 70)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
