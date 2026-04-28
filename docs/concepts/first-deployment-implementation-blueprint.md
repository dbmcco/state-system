# First Deployment Implementation Blueprint

This blueprint turns the design contracts into an implementation path while
preserving the end-state architecture.

The first deployment should be small, but it should not be disposable. Every
module should map to an end-state interface that can later use database,
service, API, or PAIA adapters.

## Objective

Build a local, inspectable deployment that can run the Laura campaign-audience
scenario end to end:

```text
trigger
  -> model review packet
  -> model proposal output
  -> commit result
  -> state journal entry
  -> agent memory entry
  -> materialized snapshot
  -> rollup request
  -> review signal
```

## Proposed Module Boundaries

### `contracts`

Owns schema loading and validation.

Responsibilities:

- load JSON schemas
- validate examples and runtime payloads
- expose stable contract names
- keep schema validation separate from business meaning

### `stores`

Owns persistence interfaces.

Initial adapters:

- `FileStateStore`
- `FileJournalStore`
- `FileMemoryStore`
- `FileRollupQueue`
- `FileReviewSignalStore`

End-state adapters:

- database-backed state store
- `paia-memory` evidence and memory adapter
- event-backed rollup queue

### `runner`

Owns the Notice phase.

Responsibilities:

- accept a trigger
- validate trigger schema
- resolve evidence refs
- load state snapshots
- load recent journals
- load relevant agent memory
- load persona context
- build model review packet

It should not decide what changed.

### `reviewer`

Owns the Interpret phase.

Responsibilities:

- send model review packet to model
- request output matching `model-proposal-output.schema.json`
- validate model output shape
- return no-op, proposals, uncertainty, missing evidence, and review signal

In test mode, this can use a fixture reviewer that returns
`examples/laura-model-proposal-output.json`.

### `committer`

Owns the Commit and Propagate phases.

Responsibilities:

- validate model proposal output
- apply governance checks
- convert accepted state proposals into journal entries
- convert accepted memory proposals into memory entries
- queue rollup requests
- materialize snapshots
- emit commit result and review signal

It should not reinterpret Laura's marketing judgment.

### `cli`

Owns the first access surface.

Initial commands:

- `state validate`
- `state trigger <trigger-file>`
- `state get <state-id>`
- `state journal <state-id>`
- `state memory <agent-id>`
- `state rollups`

The CLI is an access adapter, not the architecture.

## Runtime Directory Shape

```text
state/
  objects/
  journals/
  memory/
  review-signals/
  rollups/
  commits/
```

The current `examples/` directory should remain fixtures. Runtime state should
be generated under `state/`.

## First End-To-End Trace

The Laura fixture set should form a complete contract trace:

```text
examples/laura-campaign-audience-trigger.json
  -> examples/laura-model-review-packet.json
  -> examples/laura-model-proposal-output.json
  -> examples/laura-commit-result.json
  -> examples/marketing-campaign-audience-journal-entry.json
  -> examples/laura-agent-memory-entry.json
  -> examples/laura-review-signal.json
```

Pressure-test finding:

- The trace originally referenced
  `journal.campaign.launch-positioning-v1.audience-clarified` without a matching
  journal fixture.
- The trace should include that journal entry so every accepted commit ref has a
  corresponding durable example.

## First Verification Checks

Before code exists, verification is fixture consistency:

- all JSON parses
- trigger id links into review packet
- review packet id links into model output
- model output id links into commit result
- accepted journal refs exist as examples
- accepted memory refs exist as examples
- review signal refs match commit result refs

After code exists, these become automated tests.

## Implementation Order

1. Add schema validation utility.
2. Add fixture consistency tests.
3. Add file-backed stores.
4. Add fixture reviewer.
5. Add committer conversion from model output to journal/memory/commit result.
6. Add snapshot materializer.
7. Add CLI commands.
8. Replace fixture reviewer with model reviewer.
9. Add optional `paia-memory` adapter.

## Pressure-Test Questions For Each Step

Ask at every step:

1. Is this an end-state interface or a local-only shortcut?
2. Is business judgment being hardcoded?
3. Is provenance preserved?
4. Can a no-op pass cleanly?
5. Can pending approval avoid mutation?
6. Can the same trigger be replayed without duplicate commits?
7. Can this later use `paia-memory` or `paia-agent-runtime` without redesign?

## Current Gaps

- The model reviewer prompt is not defined.
- Governance policy objects are still conceptual.
- File-backed idempotency rules are not defined.
- Promotion proposal persistence needs a pending-approval record shape.
- The `paia-memory` adapter boundary is not specified in detail.
