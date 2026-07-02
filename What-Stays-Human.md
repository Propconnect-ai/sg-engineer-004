# What Stays Human

**Scope:** The decisions that intentionally remain under human authority in a system that automates extensively. This document explains why those decisions are not automated. It introduces no new architecture, approval workflow, or governance process; every decision here already follows from the locked ADRs and approved engineering documents. Where a decision is reserved for a human elsewhere in the packet, this document states why.

This is not an ethics document or a discussion of automation's limits. It concerns accountability, not capability.

---

## 1. Purpose

The architecture automates aggressively where automation is appropriate: ingestion, durable recording, projection, replay, and recovery are all deterministic operations the system performs without human intervention. That is by design — the platform's reliability depends on these operations running the same way every time.

A separate class of decision remains human. These are decisions whose consequences extend beyond technical correctness — into customer impact, compliance accountability, or the acceptance of architectural risk. This document identifies those decisions and states why each is reserved for a person. The organizing distinction is not whether a decision *could* be automated; it is whether someone must be *accountable* for its outcome.

## 2. Principle

Automation performs deterministic, repeatable operations whose correctness is fully defined by the system's rules. A human retains authority over decisions whose consequences are not fully captured by technical correctness — decisions that trade off business risk, carry compliance accountability, or commit the system to an irreversible change.

This is an operational-safety principle, not a limitation. The goal is not to maximize automation; it is to maximize reliable operation. A decision is automated when doing so is safe and repeatable, and reserved for a human when its consequence requires accountability that a process cannot hold.

## 3. Decisions That Stay Human

Each decision below is reserved for a person in the locked documents. This section states why.

**Approving production cutover.** Validation produces the evidence that acceptance criteria are met; a person decides to act on it. Cutover moves customer-facing reads to the proposed platform — a decision with direct customer consequence that the evidence informs but does not make. The system can show the criteria are satisfied; it cannot own the decision to proceed.

**Initiating rollback.** The Rollback Strategy reserves this for a person. Rollback conditions are drawn from observed failures, but declaring that reads must return to the existing system is a customer-facing judgment. Its consequence — returning authority, preserving evidence, accepting the halt to adoption — is a responsibility a person carries, not a threshold a process trips.

**Interpreting an unexplained validation difference.** The Validation Strategy treats an unexplained discrepancy as a defect, not noise. Determining whether such a difference is a proposed-system bug or an existing-system loss requires judgment about which explanation is correct, and accountability for the conclusion. Automation surfaces the difference; a person adjudicates it.

**Deciding whether to reopen a locked decision.** The project's governance reserves reopening an ADR for defined conditions, and the judgment that such a condition has genuinely been met — that a discovered issue is architectural rather than incidental — is a human one. Committing the team to revisit a locked decision is an accountability-bearing act.

**Approving a change to identity policy.** Introducing probabilistic identity resolution, deferred by scope in ADR-004, is not merely a technical extension. It changes the correctness and compliance posture of identity — a merge that fuses two people has consequences beyond technical correctness. Adopting it is a decision a person must own, not one the system may take on evidence alone.

**Approving a data-erasure action where accountability is required.** GDPR/CCPA erasure is executed by the system, but where an erasure carries compliance or legal consequence — an ambiguous request, a low-confidence identity association, a contested deletion — the decision to proceed requires accountability the system cannot hold. The mechanism is automated; the responsibility for a consequential erasure is not.

**Accepting an architectural trade-off, and judging when an assumption no longer holds.** The design rests on stated assumptions and deliberate trade-offs. Deciding that an assumption has stopped describing the problem — that the conditions in *What Breaks This Design* have been reached — is a judgment about the business and operating context, not a value the system computes. Accepting the associated trade-off is a human responsibility.

**Approving retirement of the existing platform.** The Migration Strategy names this the point of no return. Once the existing system is decommissioned, rollback as defined no longer applies. Committing to that irreversibility — deciding the proposed platform is stable enough to remove the fallback — is the most consequential human decision in the migration, and deliberately not automated.

## 4. Deliberate Non-Goals

The following are not goals of this document or the system's operating model:

- **Maximizing automation for its own sake.** The system automates where automation is safe and repeatable, and no further. Reserving a decision for a person is a correct outcome, not an unfinished one.
- **Human sign-off on deterministic operations.** Ingestion, projection, replay, and recovery run without human intervention by design; inserting human approval into these would reduce reliability, not increase it. The line is drawn at consequence, not at every operation.
- **A general approval or governance framework.** This document reserves specific accountability-bearing decisions already identified in the packet; it does not define a broader process, which is out of scope.

## 5. Closing Statement

The system automates deterministic, repeatable work and reserves accountability-bearing decisions for people. The distinction is not one of capability but of responsibility: automation executes what is fully defined by the system's rules, and a person owns what carries consequence beyond technical correctness.

This division is a reliability decision. A system that automated its consequential decisions would remove the accountability those decisions require; a system that required human sign-off on its deterministic operations would sacrifice the reliability automation provides. The architecture is drawn deliberately between the two — automating for reliability, reserving for accountability — because that division is what allows a small team to operate it safely.
