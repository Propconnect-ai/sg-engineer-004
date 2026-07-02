# AI Usage Disclosure

This document records how AI tools were used to produce this engineering packet, where human judgment remained authoritative, and how output quality was validated. It is a process record, not a policy statement. It describes only what happened.

## Process

The packet was produced through a review-board-style process using three models with deliberately separated responsibilities. The separation was the point: rather than ask several models the same question and average the answers — which tends to amplify shared blind spots — each model was assigned a distinct role so that one model's output could be challenged by another's independent perspective. The goal was to reduce confirmation bias, not to multiply agreement. The models did not vote on decisions. Agreement between models was never treated as evidence that a decision was correct; each recommendation was evaluated independently against the architecture and the available evidence.

ChatGPT acted as my primary design collaborator across the project — helping explore alternatives, pressure-test reasoning, and sequence the work. Claude acted as the primary technical writer for the architecture documents, drafting them after the relevant design decisions had already been made and locked. Gemini was used specifically as an independent reviewer in the role of a Principal Engineer on an architecture review board: its job was to challenge important documents, not to generate them. Assigning the reviewer role to a different model from the one that drafted the work was intentional, so that review was genuinely independent of authorship.

## Where AI was used

AI assisted with the reasoning and writing around the design, not the building of any system. Concretely, it helped explore architectural alternatives before decisions were fixed; refine the architecture decision records once a direction was chosen; improve the structure and clarity of documents; surface operational risks that were not obvious in a first pass; and review the migration, validation, and rollback strategies for gaps and inconsistencies. It was used to check consistency across documents — whether a claim in one document was contradicted by another — and to challenge assumptions that had been stated too confidently. Throughout, its contribution was to reasoning and technical precision.

No system was built or tested by AI. There is no running production system in this packet. The one executable artifact — the durability invariant test — proves a correctness property under a deterministic failure model; it and the cost model were run and verified directly, not asserted by a model.

## Where responsibility remained human

Responsibility for correctness did not transfer to any AI at any point. I selected the final architecture. I accepted or rejected each recommendation on its merits, and made every architectural trade-off myself. I decided the scope boundaries — what the design would and would not attempt — and I decided what entered the final packet and what was left out. I verified consistency across the documents rather than assuming it. Where a model proposed something, I reviewed it independently before accepting it, and rejected suggestions that did not hold up.

The evidence work was mine. I produced the AWS Pricing Calculator estimates by entering each service's configuration myself, captured the resulting screenshots and the exported estimate, confirmed the ClickHouse pricing against the vendor's published rates, and assembled the evidence repository. Where a figure is labeled calculator-verified, it is because I generated and checked that figure, not because a model reported it.

## Validation

Important documents were challenged by the independent reviewer model before being accepted, and then reviewed by me before being locked. This applied to the migration strategy, the validation strategy, the rollback strategy, the analysis of what breaks the design, the statement of what stays human, and the cost validation. In each case the review produced specific objections or refinements, which I evaluated individually. A recommendation was adopted only when it improved correctness or the quality of the evidence — not because it was offered, and not to reach agreement. Several suggestions were declined because they did not meet that bar. The review process was a filter, not a rubber stamp.

## Limitations

Human review existed specifically to catch a failure mode that AI writing is prone to: wording that claims more than the evidence supports. This occurred more than once in this project. On at least one occasion, draft language referred to pricing evidence — calculator screenshots — before that evidence had actually been produced; the correct response was to build the evidence first and only then make the claim, which is what happened. On another, an executable cost model initially produced figures that did not match the calculator-verified numbers it was meant to reproduce, and it was reconciled to the authoritative source before being accepted. In both cases the claim was corrected to match reality rather than the reverse.

As a result of that review, every assumption in the packet remains explicitly labeled, and every numerical estimate is marked as Observed, Estimated, Benchmarked, or Assumed, so that the basis of each number is visible rather than implied. Claims that would have implied evidence that did not exist were removed. The evidence log assigns each claim the highest tier that honestly supports it and no higher, and states plainly what the packet does not claim — no production deployment, no customer data, no independent verification.

The point of recording these limitations is not to fault the tools. It is to be accurate about how the packet was produced. AI contributed to exploration, drafting, and independent review throughout the project. Responsibility for the architecture, the evidence, and every accepted claim remained mine.
