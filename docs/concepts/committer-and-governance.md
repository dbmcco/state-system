# Committer And Governance

The committer turns model proposals into durable state-system effects.

It does not reinterpret business meaning. The model decides what changed and
what should be proposed. The committer decides what is valid, allowed,
persisted, pending, or rejected.

## Boundary

The model may propose:

- state updates
- memory writes
- promotion from agent memory to shared state
- actions
- rollup requests
- missing evidence
- review signals

The committer may produce:

- appended state journal entries
- persisted agent memory entries
- queued rollup requests
- materialized snapshot refs
- pending approval records
- rejected proposal records
- final review signal

The committer should not decide whether the campaign is good, whether a market
belief is strategically important, or whether Laura's interpretation is sharp.
Those are model judgments.

## Governance Checks

The committer checks:

- model output schema validity
- target state object existence
- actor write authority
- evidence reference presence
- approval requirements
- protected state rules
- action risk
- duplicate trigger or duplicate journal ids
- memory write policy
- promotion authority

Each check should produce an explicit result. Silent fallback is not allowed.

## Commit Outcomes

### Accepted

The proposal passes validation and does not require approval.

Effects:

- append journal entry
- persist memory entry, if any
- materialize affected snapshot
- queue rollup requests
- emit review signal

### Pending Approval

The proposal may be valid but requires human or authorized approval.

Effects:

- do not mutate protected state
- do not execute risky action
- record pending proposal
- emit `pending_approval` review signal

### Rejected

The proposal is invalid, unauthorized, unsupported, or unsafe.

Effects:

- do not append state journal entry
- do not persist memory entry
- emit `rejected` review signal with reason

### No-Op

The model intentionally proposes no durable update.

Effects:

- append nothing
- emit `no_update_warranted` review signal when useful for audit or operator
  visibility

## Proposal Conversion

The committer converts accepted model proposals into durable records:

```text
state_proposal -> StateJournalEntry
memory_proposal -> AgentMemoryEntry
promotion_proposal -> StateJournalEntry, possibly pending approval
rollup_request -> pending rollup queue entry
review_signal -> ReviewSignal
```

Promotion proposals are special. They originate from agent memory but target
shared organizational state. They should usually become pending unless the actor
has authority over the target state object.

## Idempotency

The committer must be idempotent around trigger and proposal ids.

If the same trigger is processed twice, the committer should not append duplicate
journal entries or duplicate memory writes. It should return a commit result
that explains the duplicate handling.

## Minimal Commit Result

The draft result contract is `schemas/commit-result.schema.json`.

It records:

- model output id
- status
- accepted journal refs
- accepted memory refs
- materialized snapshot refs
- queued rollups
- pending approvals
- rejected proposals
- final review signal

This is the operator-facing receipt for what actually happened after model
review.
