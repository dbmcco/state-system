# Model-Mediation Drift Memory Loop

Model-mediated architecture drift should enter State System as evidence, not as
automatic memory or state.

Speedrift and `archdrift` can notice that a change sits near a model-owned
decision. State System decides whether that finding means anything durable:
an agent learned a repeated failure mode, a project has an unresolved
architecture deviation, a Workgraph follow-up is needed, or no durable update is
warranted.

## Boundary

```text
Speedrift / archdrift = candidate drift finding
Workgraph = execution task and follow-up ownership
State System = durable interpreted memory, state, and review signals
GitHub = source history and collaboration evidence
```

The finding is not the memory. The finding is a source fact that can trigger
model review.

## Source Event Shape

A model-mediation drift finding should first become a source event using the
existing `source-event` contract.

Recommended mapping:

- `source_system`: `speedrift`
- `source_event`: `drift.model_mediation_finding`
- `source_event_id`: stable finding id from the drift report
- `actor_ref`: the agent, checker, or runtime that produced the finding
- `source_refs`: Speedrift finding ref, Workgraph task ref, changed file refs,
  GitHub commit or PR refs when available
- `change.kind`: `model_mediation_candidate`
- `change.object_ref`: the Workgraph task or repo path under review
- `change.payload_summary`: concise finding summary and subtype
- `candidate_state_refs`: project, capability, decision area, or operating
  picture state objects that might need review
- `candidate_persona_refs`: agent personas that may need memory, such as Codex,
  Claude Code, Patrick, or a long-lived architecture reviewer
- `idempotency.key`: stable `speedrift:<repo>:<task>:<finding-id>` key

The event may include model-mediation fields inside `change.old_value` or
`change.new_value` if the source event schema is not yet specialized:

```json
{
  "type": "possible_model_agency_violation",
  "subtype": "routing_violation",
  "profile": "advisory",
  "decision": "unknown",
  "current_owner": "unknown",
  "expected_owner": "model",
  "deviation_path": "docs/model-mediated/MODEL_MEDIATED_DEVIATION_REGISTER.md",
  "workgraph_followup_suggested": false
}
```

Do not add specialized schema fields until fixtures prove the generic envelope
is too weak.

## Review Packet

The runner should package the source event with enough context for the model to
judge durable meaning:

- the Speedrift finding and lane output
- the Workgraph task title, description, status, dependencies, and validation
  logs
- touched code and architecture docs by reference, not by copying large diffs
- the model-mediated doctrine or local architecture document
- existing deviation register entries
- relevant agent memory about repeated coding behavior
- current project, capability, decision-area, or operating-picture state
- governance constraints for memory writes, shared-state promotion, and action
  proposals

The review question is not "did the regex match?" It is:

```text
Did this work preserve model ownership of semantic judgment, or does the system
now need a redesign, explicit deviation, memory update, missing evidence, or
follow-up task?
```

## Model Proposal Outcomes

The model reviewer can return any normal `ModelProposalOutput`.

Common outcomes:

- `no_op`: the finding was a candidate only; no durable lesson or action is
  warranted.
- `needs_evidence`: the reviewer needs the relevant architecture doc, code diff,
  prompt, model output contract, or deviation record before deciding.
- `propose_updates`: the finding reveals a real project or capability state
  update, such as an unresolved model-ownership decision.
- `needs_approval`: a deterministic exception is justified but should be logged
  as a deviation requiring human approval.
- `reject`: the proposal is unsupported, unsafe, or outside the actor's
  authority.

Useful proposal classes:

- `memory_proposals`: recurring agent behavior, such as "when implementing
  model-mediated routing, this coding agent tends to add lexical heuristics
  before checking the model-ownership boundary."
- `state_proposals`: project/capability/decision-area updates, such as
  "intent routing architecture has an unresolved model-agency deviation."
- `promotion_proposals`: move a repeated agent-memory lesson into shared
  architecture doctrine after review.
- `action_proposals`: create or update a Workgraph task, add a deviation entry,
  request architecture panel review, or require test coverage.
- `missing_evidence`: request files, diffs, logs, model prompts, or output
  examples needed to decide.

## Memory Pattern

Memory should be specific, evidenced, and scoped.

Good memory:

```text
memory_key: development.pattern.model_mediation.heuristic_drift
layer: draft
memory_type: lesson
summary: Coding agents repeatedly replace model judgment with deterministic
  routing shortcuts during implementation.
evidence_refs:
  - speedrift:repo:archdrift:task:model-mediated-speedrift-check-surface:finding:...
  - workgraph:repo:experiments:task:model-mediated-speedrift-check-surface
promotion_status: candidate
```

Weak memory:

```text
Models are bad at architecture.
```

State System should prefer draft or searchable memory until there are repeated
evidence-backed cases. Promotion into shared state should require an explicit
review signal.

## Deviation Handling

A deviation is acceptable only when it is intentional and recorded.

The reviewer should ask:

- what decision did deterministic code take from the model?
- why is that exception necessary?
- what scope limits it?
- what evidence proves it is safer or required?
- how will the exception be tested?
- where is the deviation recorded?
- when should it be revisited?

Deviation records belong with architecture docs or a dedicated deviation
register. State System can remember that the deviation exists, track review
pressure, and propose Workgraph follow-ups, but it should not become the source
of truth for code architecture by itself.

## Workgraph Feedback

State System may propose Workgraph actions through normal action proposals.

Examples:

- create a task to remove deterministic routing from a model-mediated path
- create a task to add a model-owned classification fixture
- create a task to document an approved deviation
- create a task to run the model-mediated architecture panel
- create a task to update the skill if a repeated failure pattern becomes
  doctrine

The committer or downstream adapter owns whether those proposals become actual
Workgraph tasks. The model reviewer should not call `wg add` directly.

## Governance

The committer remains the authority boundary.

It may accept:

- memory entries with evidence refs
- review signals
- non-protected state updates within actor authority
- low-risk internal action proposals

It should hold for approval:

- shared doctrine changes
- protected project or capability state
- deviations that bless deterministic ownership of model judgment
- external actions
- broad policy changes that affect multiple repos or agents

It should reject:

- proposals without evidence refs
- proposals that copy large source blobs instead of refs
- claims that a violation exists when the packet only proves a candidate
- attempts to mutate Workgraph, GitHub, or code directly from reviewer output

## Closed Loop

```text
Speedrift finding
  -> source event
  -> model review packet
  -> model proposal output
  -> committer/governance
  -> memory, state, review signal, or pending action
  -> recent-change index
  -> future agent context package
  -> better implementation discipline
```

The loop matters because one-off drift warnings are easy to ignore. Durable
memory should help future agents see the pattern before they repeat it, while
keeping execution and source-control authority in the systems that already own
those boundaries.
