# First Deployment Implementation Blueprint

This blueprint turns the design contracts into an implementation path while
preserving the end-state architecture.

The first deployment should be small, but it should not be disposable. Every
module should map to an end-state interface that can later use database,
service, API, or PAIA adapters.

## Objective

Build a local, inspectable deployment that can run three comparison scenarios end
to end:

- Laura campaign-audience clarification, which tests marketing interpretation
  and agent memory.
- Patrick stale-contract review, which tests operational state hygiene, missing
  evidence, and governance boundaries.
- Patrick GitHub launch-readiness review, which tests source-system evidence,
  code commits versus delivery commitments, multi-state proposals, and proposed
  Workgraph follow-up.

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

## First End-To-End Traces

The Laura fixture set forms a complete contract trace:

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

The Patrick fixture set forms the comparison trace:

```text
examples/patrick-stale-contract-trigger.json
  -> examples/patrick-model-review-packet.json
  -> examples/patrick-model-proposal-output.json
  -> examples/patrick-commit-result.json
  -> examples/patrick-contract-journal-entry.json
  -> examples/patrick-agent-memory-entry.json
  -> examples/patrick-review-signal.json
```

Pressure-test finding:

- Laura alone could make the system look like a marketing memory tool.
- Patrick forces the same contracts to handle operational source-of-truth
  discipline, missing evidence, internal follow-up, and approval boundaries.

The GitHub commitment fixture set forms the ecosystem integration trace:

```text
examples/patrick-github-launch-readiness-trigger.json
  -> examples/patrick-github-launch-readiness-model-review-packet.json
  -> examples/patrick-github-launch-readiness-model-proposal-output.json
  -> examples/patrick-github-launch-readiness-commit-result.json
  -> examples/patrick-github-capability-journal-entry.json
  -> examples/patrick-github-obligation-journal-entry.json
  -> examples/patrick-github-launch-readiness-agent-memory-entry.json
  -> examples/patrick-github-launch-readiness-review-signal.json
```

Pressure-test finding:

- A GitHub merge is implementation evidence, not launch readiness.
- A PR review comment can create or preserve a delivery obligation.
- One trigger can validly produce multiple state proposals.
- Proposed Workgraph follow-up should remain an action proposal; Workgraph owns
  task creation and execution.

## First Verification Checks

Before code exists, verification is fixture consistency:

- all JSON parses
- trigger id links into review packet
- review packet id links into model output
- model output id links into commit result
- accepted journal refs exist as examples
- accepted memory refs exist as examples
- review signal refs match commit result refs
- Laura, Patrick stale-contract, and Patrick GitHub commitment traces pass the
  same consistency checks
- multi-state traces can accept multiple journal refs and materialized snapshots

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
- File-backed idempotency rules are not defined.
- Promotion proposal persistence needs a pending-approval record shape.
- The `paia-memory` adapter boundary is not specified in detail.
