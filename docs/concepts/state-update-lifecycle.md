# State Update Lifecycle

The state update lifecycle defines how a change becomes durable state.

The lifecycle must preserve two constraints:

1. The journal is the source of truth.
2. The model decides meaning; code enforces contracts, permissions, persistence,
   and auditability.

## Lifecycle Stages

These stages are a conceptual checklist, not a requirement to build ten
separate runtime components.

```text
trigger
  -> evidence packet
  -> relevance selection
  -> model review
  -> journal proposal
  -> governance gate
  -> journal append
  -> snapshot materialization
  -> rollup queue
  -> review signal
  -> recent-change registry
```

## Practical Runtime Shape

The implementation should feel like a five-phase loop:

1. Notice: receive a trigger and gather an evidence packet.
2. Interpret: ask the model what changed, what matters, what is uncertain, and
   which state objects are affected.
3. Commit: validate schema, authority, evidence, and risk; append journal
   entries; materialize snapshots.
4. Propagate: queue rollups, emit review signals, and surface follow-up.
5. Index: record accepted changes for recent-change and agent opportunity
   review.

The detailed stages below exist to prevent concern-blending. They should not
turn the system into ceremony.

## 1. Trigger

A trigger is any event that might change state.

The draft generic trigger contract is `schemas/trigger.schema.json`.

Examples:

- human edit
- meeting completed
- message received
- task changed
- document edited
- tool result returned
- metric updated
- scheduled review started
- agent reasoning cycle completed

Triggers do not mutate snapshots directly. They create an update opportunity.

## 2. Evidence Packet

The system builds an evidence packet from factual inputs.

The packet may include:

- trigger reference
- trigger payload summary
- source excerpts or identifiers
- actor identity
- timestamp
- affected state object ids, if known
- available persona id, if a persona is reviewing the change
- relevant governance constraints

The evidence packet should prefer references over copied content. Large source
material should remain in its system of record.

## 3. Relevance Selection

The system identifies likely relevant state objects.

Code may retrieve candidates by explicit ids, ownership, recent activity,
source-system links, or broad search. The model should decide which candidates
matter to the update and whether other state objects should be inspected.

This is a model-mediated boundary:

- Code can find and load candidates.
- The model decides relevance, salience, uncertainty, and whether the update
  should affect a state object.

## 4. Model Review

The model receives:

- the evidence packet
- relevant current snapshots
- recent journal entries
- persona and facet context, when applicable
- governance state
- available update tools

The model answers:

- what changed?
- what did not change?
- what is fact versus interpretation?
- what evidence supports the interpretation?
- what uncertainty remains?
- which state objects should be updated?
- which actions should be proposed?
- which rollups may need regeneration?

The model may also decide that no durable update is warranted.

## 5. Journal Proposal

A journal proposal is the model's proposed state transition before persistence.

It includes:

- target state object id
- update class
- interpretation
- state patch
- evidence references
- uncertainty
- proposed actions
- affected parent or child state refs
- rollup requests
- approval requirement, if any

Journal proposals are allowed to be rejected, revised, or held for review.

## 6. Governance Gate

Code checks the proposal against governance state and system policy.

See `docs/concepts/committer-and-governance.md` for the committer boundary and
commit result contract.

The gate checks:

- schema validity
- actor authority
- target object write permission
- evidence reference existence
- action risk and approval boundaries
- whether the patch attempts to overwrite protected state
- whether required review is missing

The governance gate should not decide business meaning. It should decide whether
the proposed transition is allowed to become durable state.

## 7. Journal Append

If the proposal passes the governance gate, the system appends a journal entry.

Journal entries are immutable. Corrections require a later journal entry.

Each appended entry should identify:

- source trigger
- actor
- target state object
- update class
- interpretation
- state patch
- evidence refs
- uncertainty
- proposed or taken actions
- approval status, if relevant

## 8. Snapshot Materialization

The snapshot is regenerated or patched from journal history.

Patch and replay semantics are defined in
`docs/concepts/materialization-and-patch-semantics.md`.

The materializer should:

- apply accepted journal entries in order
- preserve local truth owned by the state object
- keep evidence references visible
- update `as_of`
- update `latest_journal_entry_id`
- avoid smuggling rollup conclusions into child objects

Humans and agents usually read snapshots first because they are compact. They
inspect journal history when they need provenance, disagreement, or nuance.

## 9. Rollup Queue

Some updates affect parent state.

Examples:

- a campaign update may affect a marketing operating picture
- a deal update may affect revenue pipeline state
- an onboarding update may affect role readiness
- a mission clarification may affect persona and work evaluation

The initial update should not blindly rewrite every parent. It should enqueue
or request rollup review for affected parents. Rollup review follows the same
lifecycle: trigger, evidence packet, model review, journal proposal, governance,
journal append, snapshot materialization.

## 10. Review Signal

The lifecycle ends by emitting a review signal.

The draft generic review signal contract is
`schemas/review-signal.schema.json`.

Possible outcomes:

- no durable update warranted
- journal appended and snapshot materialized
- proposal requires human approval
- proposal rejected by governance
- evidence missing
- rollup review queued
- conflict or uncertainty requires follow-up

Review signals are useful for operating pictures and for agent onboarding: they
show whether the system is actually staying current.

## 11. Recent Change Registry

The lifecycle should index accepted commits, review signals, and relevant source
events into a recent-change registry.

The registry is not the source of truth. The journal remains the source of
truth. The registry is an access surface that helps humans and agents ask:

- what changed recently?
- which state objects were affected?
- what evidence supports the change?
- which agents or personas might care?
- what opportunities or follow-ups might need review?

This is especially important for agents. Laura may watch recent deal,
relationship, campaign, capability, or operating-picture changes for marketing
opportunities. Patrick may watch recent task, obligation, contract, project, and
GitHub changes for operational follow-up.

The registry should surface candidate changes. The model decides whether any
candidate is meaningful enough to propose a state update, memory write, action,
or approval-gated external publication.

## Update Classes

### Direct Update

A direct update changes one state object from one trigger.

Example: a human clarifies Laura's authority boundary.

### Interpretive Update

An interpretive update records model judgment over ambiguous evidence.

Example: Laura judges that a campaign is not ready for external publication
because the audience and proof are underspecified.

### Corrective Update

A corrective update revises or contradicts prior state.

Example: a later customer interview disproves an earlier market belief.

The old journal entry remains. The correction becomes a new entry with evidence.

### Rollup Update

A rollup update regenerates parent state from child state.

Example: several campaign and relationship updates change the marketing
operating picture.

### Developmental Update

A developmental update changes readiness or learning state.

Example: a human or agent completes onboarding for a role, gains tool access, or
still lacks required context.

## Approval Posture

Not every update needs human approval.

Low-risk internal interpretations can be appended automatically when evidence
and permissions are sufficient. External commitments, protected mission changes,
policy changes, relationship-sensitive claims, or actions with business risk may
require approval.

Approval should attach to the journal entry or proposed action, not disappear
into chat context.

## Minimal Runtime Contract

The smallest useful lifecycle runner needs to do only this:

1. Accept a trigger.
2. Build an evidence packet.
3. Load relevant snapshots and recent journals.
4. Ask a model to produce zero or more journal proposals.
5. Validate proposals against schema and governance.
6. Append accepted journal entries.
7. Materialize affected snapshots.
8. Queue rollup reviews.
9. Return a review signal.

Storage, queueing, and integrations can change later. This lifecycle contract
should remain stable.
