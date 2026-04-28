# Minimum Viable Runtime

The minimum viable runtime should prove the state loop without turning the
design repo into an infrastructure project too early.

The goal is not to build the final storage, queueing, search, or integration
layer. The goal is to answer one question:

Can a model-mediated agent notice evidence, interpret what changed, append a
journal entry, materialize a snapshot, and request rollups without losing
provenance or violating authority boundaries?

## Runtime Posture

Start local, explicit, and inspectable.

- local files before database
- CLI before daemon
- JSON before custom persistence
- explicit trigger files before live integrations
- manual command invocation before scheduled automation
- one persona and one domain before many agents

This keeps the runtime close to the design artifacts and makes failures easy to
inspect.

## Four Components

### 1. State Store

The state store owns durable files.

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
  rollups/
    pending.jsonl
```

The current `examples/` directory stays as design fixtures. Runtime state should
live under a separate `state/` directory when implementation begins.

### 2. Trigger Runner

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
  "actor_ref": "human.braydon",
  "summary": "Laura's approval boundary was clarified.",
  "evidence_refs": ["conversation.2026-04-28.state-system"],
  "candidate_state_refs": ["persona.laura"]
}
```

The runner should gather candidate snapshots and journals, then hand them to the
model. It should not decide business meaning.

### 3. Model Reviewer

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
- rollup requests
- review signal

The model may decide that no durable update is warranted. That outcome matters:
it prevents state churn.

### 4. Committer

The committer is the safety and persistence layer.

Responsibilities:

- validate journal proposals against schema
- verify evidence refs are present or explicitly unresolved
- check actor authority and action approval boundaries
- append accepted journal entries
- materialize affected snapshots
- record rejected or pending proposals as review signals
- queue requested rollups

The committer does not decide whether a campaign is strategically weak, a
relationship is warming, or an onboarding process is ready. Those are model
judgments.

## First Vertical Slice

The first runnable slice should use Laura and marketing campaign state.

Scenario:

1. Trigger says a human clarified the campaign's primary audience.
2. Runner loads Laura, the campaign snapshot, the marketing operating picture,
   and recent campaign journal entries.
3. Model proposes an interpretive journal entry for the campaign.
4. Committer validates and appends it.
5. Snapshot materializer updates the campaign snapshot.
6. Rollup request is queued for marketing operating picture.

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
state loop.

## Implementation Interfaces

The first implementation should expose a small set of commands or functions:

- `state validate`: validate schemas and state files
- `state get <state-id>`: print current snapshot
- `state journal <state-id>`: print journal history
- `state trigger <trigger-file>`: run the model-mediated update loop
- `state materialize <state-id>`: rebuild a snapshot from journals
- `state rollups`: inspect pending rollup requests

The command names are placeholders for design clarity. The important point is
the capability boundary, not the exact CLI syntax.

## Success Criteria

The MVP works when:

- a trigger can create a journal proposal
- the model can choose no-op, update, or rollup request
- accepted proposals append immutable journal entries
- snapshots can be regenerated from journals
- evidence refs and uncertainty remain visible
- approval-required actions are not executed automatically
- a human can inspect every file involved

## Next Design Question

Before implementation, define the first trigger schema and review-signal schema.
Those are the contracts between the runner, model reviewer, and committer.
