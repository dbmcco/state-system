# First Deployment Mode

The first deployment mode should prove the end-state architecture without
turning the design repo into an infrastructure project too early.

The goal is not to build a temporary architecture. The goal is to run the same
interfaces locally before connecting database-backed stores, APIs, queues, and
integrations.

Can a model-mediated agent notice evidence, interpret what changed, append a
journal entry, materialize a snapshot, and request rollups without losing
provenance or violating authority boundaries?

See `docs/concepts/end-state-architecture.md` for the target architecture this
deployment mode should serve.

## Runtime Posture

Start local, explicit, and inspectable, while preserving end-state interfaces.

- local store adapter before database-backed store
- CLI access surface before API/UI access surfaces
- JSON files before durable persistence service
- explicit trigger files before live integrations
- manual command invocation before scheduled automation
- one persona and one domain before many agents

This keeps failures easy to inspect without creating a local-only design.

## Six Interfaces

The first deployment should implement or stub the same interfaces expected in
the end state.

### 1. Evidence Store

The evidence store resolves source references and retrieves relevant source
records.

Initial local behavior can be simple reference checking. The end-state adapter
may use `paia-memory` evidence, embeddings, digests, and retrieval.

### 2. Memory Store

The memory store owns agent-specific learned memory.

Initial local behavior can read and write JSON fixtures. The end-state adapter
may use `paia-memory` facets, triplets, semantic retrieval, and active context.

### 3. State Store

The state store owns durable state objects and journals.

Initial responsibilities:

- read snapshots
- append journal entries
- write materialized snapshots
- list state objects by id, type, family, owner, and parent refs
- preserve append-only journal history

The first implementation can be a directory structure, not a service.

```text
state/
  objects/
    state.org.mission.json
    state.campaign.launch-positioning-v1.json
  journals/
    state.org.mission.jsonl
    state.campaign.launch-positioning-v1.jsonl
  memory/
    persona.laura.jsonl
  rollups/
    pending.jsonl
```

The current `examples/` directory stays as design fixtures. Runtime state should
live under a separate `state/` directory when implementation begins.

### 4. Trigger Runner

The trigger runner starts the four-phase loop:

1. Notice
2. Interpret
3. Commit
4. Propagate

Initial trigger input can be a JSON file:

```json
{
  "id": "trigger.example",
  "source": "human_edit",
  "actor_ref": "human.example_user",
  "summary": "Laura's approval boundary was clarified.",
  "evidence_refs": ["conversation.2026-04-28.state-system"],
  "candidate_state_refs": ["persona.laura"]
}
```

The runner should gather candidate snapshots and journals, then hand them to the
model. It should not decide business meaning.

### 5. Model Reviewer

The model reviewer is the decision layer.

Inputs:

- trigger
- evidence packet
- current snapshots
- recent journals
- persona/facet context, if applicable
- governance constraints
- allowed output schema

Outputs:

- zero or more journal proposals
- zero or more memory proposals
- rollup requests
- review signal

The model may decide that no durable update is warranted. That outcome matters:
it prevents state churn.

### 6. Committer

The committer is the safety and persistence layer.

Responsibilities:

- validate journal proposals against schema
- validate memory proposals against memory policy
- verify evidence refs are present or explicitly unresolved
- check actor authority and action approval boundaries
- append accepted journal entries
- persist accepted memory writes
- materialize affected snapshots
- record rejected or pending proposals as review signals
- queue requested rollups

The committer does not decide whether a campaign is strategically weak, a
relationship is warming, or an onboarding process is ready. Those are model
judgments.

## First Vertical Slice

The first runnable slice should use Laura, Laura's memory, and marketing
campaign state.

Scenario:

1. Trigger says a human clarified the campaign's primary audience.
2. Runner loads Laura, Laura's relevant memory, the campaign snapshot, the
   marketing operating picture, and recent campaign journal entries.
3. Model proposes an interpretive journal entry for the campaign and may propose
   a Laura memory write.
4. Committer validates and appends the journal entry.
5. Committer persists accepted memory writes.
6. Snapshot materializer updates the campaign snapshot.
7. Rollup request is queued for marketing operating picture.

This slice touches the full lifecycle while staying small.

## What To Avoid Initially

Do not start with:

- Postgres
- event bus
- long-running daemon
- embeddings or semantic search
- UI
- multi-tenant permissions
- real-time integrations
- autonomous scheduled updates
- all personas at once

These may become useful later, but they are not required to prove the core
state and memory loop.

## Implementation Interfaces

The first implementation should expose a small set of commands or functions:

- `state validate`: validate schemas and state files
- `state get <state-id>`: print current snapshot
- `state journal <state-id>`: print journal history
- `state memory <agent-id>`: inspect agent memory
- `state trigger <trigger-file>`: run the model-mediated update loop
- `state materialize <state-id>`: rebuild a snapshot from journals
- `state rollups`: inspect pending rollup requests

The command names are placeholders for design clarity. The important point is
the capability boundary, not the exact CLI syntax.

## First Contracts

The first deployment mode depends on three edge contracts:

- `schemas/trigger.schema.json`: the runner input that starts the loop
- `schemas/agent-memory-entry.schema.json`: accepted agent memory writes
- `schemas/review-signal.schema.json`: the committer output that tells humans
  and agents what happened

These sit beside the existing state contracts:

- `schemas/state-object.schema.json`
- `schemas/state-journal-entry.schema.json`
- `schemas/model-review-packet.schema.json`
- `schemas/model-proposal-output.schema.json`
- `schemas/commit-result.schema.json`

Together, these contracts let the first deployment prove the end-state loop:
trigger in, model review, journal and memory persistence, snapshot update,
rollup request, commit result, review signal out.

## Success Criteria

The first deployment mode works when:

- a trigger can create a journal proposal
- the model can choose no-op, state update, memory write, or rollup request
- accepted proposals append immutable journal entries
- accepted memory proposals persist to agent memory
- snapshots can be regenerated from journals
- evidence refs and uncertainty remain visible
- approval-required actions are not executed automatically
- a human can inspect every file involved

## Contract Derivation

The first model-mediated contracts are:

- `schemas/model-review-packet.schema.json`
- `schemas/model-proposal-output.schema.json`

They were derived from the scenario pressure test in
`docs/concepts/model-pressure-test.md`.

The implementation path and first fixture trace are described in
`docs/concepts/first-deployment-implementation-blueprint.md`.
