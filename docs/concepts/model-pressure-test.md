# Model Pressure Test

This document pressure-tests the State System model before defining the model
review packet and model proposal output contracts.

The test asks: what realistic situations should the model-mediated layer handle,
and what does each situation imply for the next schemas?

## What We Are Testing

The model here is the conceptual State System model, not one specific LLM.

We are testing whether the architecture can handle:

- organizational state
- individual agent memory
- evidence-backed interpretation
- no-op decisions
- corrections and conflicts
- governance gates
- rollups
- promotion from agent memory to shared state
- reusable PAIA memory/runtime assets

## Pass Criteria

The model is strong enough to define contracts when every scenario can answer:

1. What does the runner provide to the model?
2. What does the model decide?
3. What should code validate?
4. What is persisted?
5. What should not be persisted?
6. What rollup, follow-up, or approval is needed?

## Scenario 1: Laura Campaign Audience Clarified

**Trigger:** Braydon clarifies that the primary audience is mid-market operators
who need bounded back-office business capabilities.

**Expected model decision:**

- update campaign state as an interpretive update
- possibly write Laura memory about audience-before-copy
- queue marketing operating-picture rollup
- avoid external publishing action

**Pressure result:** passes.

**Contract implication:** model input needs trigger, campaign snapshot, Laura
persona, Laura memory candidates, recent journal entries, and governance around
external copy. Output needs both state proposals and memory proposals.

## Scenario 2: No Durable Update Warranted

**Trigger:** A message says "great" after a design checkpoint.

**Expected model decision:**

- no state patch
- no memory write unless the message resolves an explicit open question
- maybe review signal: `no_update_warranted`

**Pressure result:** passes only if the output contract allows empty proposals.

**Contract implication:** model output must represent no-op intentionally. The
committer should not treat "no proposals" as failure.

## Scenario 3: Contradictory Evidence

**Trigger:** A later LFW positioning note says public language should emphasize
"configured AI capabilities," contradicting earlier "bounded business
capabilities" language.

**Expected model decision:**

- do not overwrite the prior campaign or narrative state as fact
- create a corrective or interpretive journal proposal that records tension
- mark uncertainty
- possibly ask for human review
- keep Laura memory as a working theory, not promoted state

**Pressure result:** passes if uncertainty and correction are first-class.

**Contract implication:** model output needs conflict/uncertainty fields and an
update class. The input packet should include recent journals, not only current
snapshot, so the model can see what it may be contradicting.

## Scenario 4: Agent Memory Promotion

**Trigger:** Laura has accumulated repeated memory entries showing that LFW
messaging performs better when framed as bounded business capability.

**Expected model decision:**

- propose promoting Laura private memory into shared marketing narrative state
- cite all evidence refs
- require approval if the narrative is protected or externally significant
- leave private memory intact even after promotion

**Pressure result:** passes only if promotion is explicit.

**Contract implication:** output needs a promotion proposal, not just generic
memory write or generic state patch. Governance needs to evaluate promotion
authority and target state.

## Scenario 5: Governance Blocks External Action

**Trigger:** Laura reviews a campaign and proposes publishing external copy.

**Expected model decision:**

- it may propose the action
- it must mark approval required
- committer must not execute it automatically
- review signal should be `pending_approval`

**Pressure result:** passes.

**Contract implication:** model output can include proposed actions, but action
execution is not part of memory or state persistence. Code owns approval gating.

## Scenario 6: Human Onboarding Progress

**Trigger:** Shy completes an onboarding step and demonstrates understanding of
Linear/Git/Drive source-of-truth norms.

**Expected model decision:**

- update onboarding state as developmental
- do not mutate the durable ops-manager role state
- possibly update operating picture if readiness changes capacity
- no agent memory write unless an agent learned something from the onboarding
  process

**Pressure result:** passes if role and onboarding remain separate.

**Contract implication:** input needs parent/child state refs and state traits.
Output needs to target specific state objects, not broad families.

## Scenario 7: Operating Picture Rollup

**Trigger:** Several campaign, relationship, and SalesForge updates occur.

**Expected model decision:**

- synthesize the marketing or LFW operating picture
- preserve child refs
- avoid copying every child detail into the rollup
- identify active tensions and follow-ups

**Pressure result:** passes if rollups are treated as first-class updates.

**Contract implication:** model input for rollups needs child snapshots and
recent child journal entries. Output needs rollup proposals with child evidence
refs.

## Scenario 8: Evidence Missing

**Trigger:** A trigger claims "client approved the proposal" without a source
record.

**Expected model decision:**

- do not persist as fact
- record uncertainty or request evidence
- maybe create a follow-up action
- review signal should be `evidence_missing`

**Pressure result:** passes only if fact/interpretation distinction survives.

**Contract implication:** model output needs a way to classify evidence gaps.
Code must verify evidence refs where possible.

## Scenario 9: PAIA Memory Backend Adapter

**Trigger:** Laura searches memory for prior positioning patterns through a
`paia-memory` adapter.

**Expected model decision:**

- treat retrieved facets/triplets/evidence as memory context
- distinguish retrieved memory from shared state
- avoid promoting memory automatically
- cite memory refs when used

**Pressure result:** passes.

**Contract implication:** model input packet needs separate sections for
evidence, memory, state, persona, and governance. Flattening all context into
one blob would lose important provenance.

## Scenario 10: Agent Memory Becomes Stale

**Trigger:** Laura has an old memory saying "audience-first copy always works,"
but recent evidence shows technical buyers respond better to prototype-first
proof.

**Expected model decision:**

- create a corrective memory entry or update memory status
- do not delete the old memory silently
- possibly lower confidence
- consider whether shared marketing state needs review

**Pressure result:** partially passes.

**Contract implication:** agent memory entries need update/revision semantics.
The first schema has `confidence` and `review_notes`, but we may also need
`supersedes_ref` or `superseded_by_ref` later.

## Scenario 11: Mission Change With Broad Effects

**Trigger:** leadership changes LFW mission language.

**Expected model decision:**

- treat as protected organizational identity state
- require approval or leadership actor authority
- queue rollups or reviews for strategy, Laura persona behavior, onboarding,
  marketing narrative, and active work
- avoid immediately rewriting every child snapshot

**Pressure result:** passes.

**Contract implication:** model output needs multiple rollup/review requests and
approval status. The committer must handle protected state.

## Scenario 12: Bad Trigger Or Duplicate Trigger

**Trigger:** the same event is replayed twice, or a trigger has malformed source
metadata.

**Expected model decision:**

- duplicate should not create duplicate durable state
- malformed trigger should be rejected before model review if schema-invalid
- if semantically duplicate but schema-valid, model can no-op or code can dedupe
  by trigger id/source id

**Pressure result:** passes if trigger ids and source refs are stable.

**Contract implication:** trigger packet should carry stable ids and source refs.
Committer should be idempotent around journal append.

## Scenario 13: Patrick Contract Record Stale

**Trigger:** Patrick's scheduled operations review finds that the Harbor
contract record lacks an explicit owner, current stage, next action, and
canonical Drive archive reference.

**Expected model decision:**

- keep the Harbor obligation active as waiting on internal clarification
- propose an interpretive state update, not a resolved direct update
- request missing evidence for the current stage and canonical source
- write Patrick private draft memory about confirming canonical source before
  external follow-up
- queue an operations operating-picture rollup
- avoid approving, sending, signing, or externally committing anything

**Pressure result:** passes.

**Contract implication:** the same contracts used for Laura can handle a more
operational agent, but the review packet must preserve governance constraints
and missing evidence separately from state patches. A second persona also
confirms that professional facets are not just tone; they change what the model
notices and what it refuses to do.

## Findings

### Finding 1: The Model Packet Must Preserve Separation

The model input should not be one generic context blob.

It needs separate sections:

- trigger
- evidence packet
- current state snapshots
- recent state journals
- agent memory
- persona and facets
- governance constraints
- available proposal types

### Finding 2: The Output Must Allow No-Op

No-op is a valid model decision.

The output contract should allow zero state proposals, zero memory proposals,
zero promotion proposals, and a review signal explaining why no durable update
was warranted.

### Finding 3: Promotion Needs Its Own Shape

Promotion from agent memory to shared state is not just a memory write and not
just a state patch.

It needs:

- memory refs
- target state object
- rationale
- evidence refs
- approval status
- proposed state patch

### Finding 4: Corrections Need Provenance

The system must handle contradictions without deleting prior truth.

The model proposal output should support:

- corrective update class
- uncertainty
- conflicting refs
- confidence changes
- optional supersession fields for memory

### Finding 5: Governance Belongs After Interpretation

The model should be allowed to propose risky actions or protected updates, but
code decides whether they can be committed or executed.

The model output should mark risk and approval needs. The committer enforces.

### Finding 6: Rollups Are Reviews, Not Cascading Writes

Child updates should queue rollup review. They should not directly rewrite all
parents.

The output contract should support rollup requests separately from state
patches.

### Finding 7: Agent Memory Needs Revision Links

The current memory schema is enough for first examples, but stale or corrected
memory will need lineage.

Likely future fields:

- `supersedes_ref`
- `superseded_by_ref`
- `status`
- `last_reviewed_at`

## Contract Requirements For Next Step

### Model Review Packet

Draft schema: `schemas/model-review-packet.schema.json`.

The packet should include:

- `id`
- `trigger`
- `evidence_packet`
- `state_context`
- `journal_context`
- `memory_context`
- `persona_context`
- `governance_context`
- `allowed_outputs`

### Model Proposal Output

Draft schema: `schemas/model-proposal-output.schema.json`.

The output should include:

- `id`
- `review_packet_id`
- `decision`
- `observations`
- `state_proposals`
- `memory_proposals`
- `promotion_proposals`
- `action_proposals`
- `rollup_requests`
- `uncertainty`
- `missing_evidence`
- `review_signal`

### State Proposal

Each state proposal should include:

- target state object id
- update class
- interpretation
- patch
- evidence refs
- uncertainty
- approval requirement

### Memory Proposal

Each memory proposal should include:

- agent ref
- memory key
- layer
- memory type
- content
- confidence
- evidence refs
- related state refs
- promotion status
- optional supersession refs

### Promotion Proposal

Each promotion proposal should include:

- source memory refs
- target state object id
- rationale
- proposed state patch
- evidence refs
- approval requirement

## Result

The conceptual model is strong enough to define model review packet and model
proposal output contracts, but the contracts should explicitly support:

- no-op
- promotion
- correction
- missing evidence
- rollup request
- governance handoff
- separated context sections
- future memory revision links
