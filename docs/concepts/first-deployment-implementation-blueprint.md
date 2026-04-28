# First Deployment Implementation Blueprint

This blueprint turns the design contracts into an implementation path while
preserving the end-state architecture.

The first deployment should be small, but it should not be disposable. Every
module should map to an end-state interface that can later use database,
service, API, or PAIA adapters.

## Objective

Build a local, inspectable deployment that can run four comparison scenarios end
to end:

- Laura campaign-audience clarification, which tests marketing interpretation
  and agent memory.
- Patrick stale-contract review, which tests operational state hygiene, missing
  evidence, and governance boundaries.
- Patrick GitHub launch-readiness review, which tests source-system evidence,
  code commits versus delivery commitments, multi-state proposals, and proposed
  Workgraph follow-up.
- Linear deal-won opportunity review, which tests recent-change routing,
  context packaging, and Laura's approval-gated marketing opportunity review.

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

Contracts are the first catch point for malformed payloads.

### `stores`

Owns persistence interfaces.

Initial adapters:

- `FileStateStore`
- `FileJournalStore`
- `FileMemoryStore`
- `FileRollupQueue`
- `FileReviewSignalStore`
- `FileRecentChangeStore`
- `FileContextPackageStore`

End-state adapters:

- database-backed state store
- `paia-memory` evidence and memory adapter
- event-backed rollup queue
- event-backed recent-change registry
- generated context package cache

Stores preserve evidence, journals, recent changes, context packages, and
commit outputs so later catch points can audit what happened.

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
- load recent-change candidates when a persona is reviewing opportunities
- build model review packet

It should not decide what changed.

The runner catches source facts, evidence resolution, and candidate state
loading. It should not catch opportunity or business meaning.

### `context-packager`

Owns bounded context assembly for agents.

Responsibilities:

- build standing packages from persona, active state, memory, and governance
- build recent-change packages from routed registry entries
- build opportunity packages for a specific candidate change
- include excluded-context summaries so omissions are inspectable
- keep packaging separate from salience decisions

It should not decide whether an opportunity is real.

The context packager catches bounded working context: what the agent should see,
what was excluded, and what freshness constraints apply.

### `reviewer`

Owns the Interpret phase.

Responsibilities:

- send model review packet to model
- request output matching `model-proposal-output.schema.json`
- validate model output shape
- return no-op, proposals, uncertainty, missing evidence, and review signal

In test mode, this can use a fixture reviewer that returns
`examples/laura-model-proposal-output.json`.

The reviewer catches meaning, salience, uncertainty, and proposed action. It is
the first layer allowed to decide whether something is an opportunity.

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
- record recent-change entries for later agent opportunity review

It should not reinterpret Laura's marketing judgment.

The committer catches schema, authority, duplicate commit, freshness, and
approval problems. It does not decide whether the proposal is strategically
good.

### `cli`

Owns the first access surface.

Initial commands:

- `state validate`
- `state trigger <trigger-file>`
- `state get <state-id>`
- `state journal <state-id>`
- `state memory <agent-id>`
- `state rollups`
- `state recent --persona <persona-id>`
- `state package --persona <persona-id>`

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
  recent-changes/
  context-packages/
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

The Linear deal-won opportunity fixture set forms the recent-change and context
package trace:

```text
examples/linear-southern-abrasives-won-trigger.json
  -> examples/linear-southern-abrasives-won-model-review-packet.json
  -> examples/linear-southern-abrasives-won-model-proposal-output.json
  -> examples/linear-southern-abrasives-won-commit-result.json
  -> examples/recent-linear-southern-abrasives-won.json
  -> examples/laura-southern-abrasives-opportunity-context-package.json
  -> examples/laura-southern-abrasives-opportunity-review-packet.json
  -> examples/laura-southern-abrasives-opportunity-model-output.json
  -> examples/laura-southern-abrasives-opportunity-commit-result.json
```

Pressure-test finding:

- Linear deal-stage movement can become durable deal state.
- The same change can route to Patrick for operations and Laura for marketing.
- Laura receives a bounded opportunity package, not the full operational task
  surface.
- External LinkedIn publication remains pending approval and requires fresh
  evidence.

## First Verification Checks

Before code exists, verification is fixture consistency:

- all JSON parses
- trigger id links into review packet
- review packet id links into model output
- model output id links into commit result
- accepted journal refs exist as examples
- accepted memory refs exist as examples
- review signal refs match commit result refs
- Laura, Patrick stale-contract, Patrick GitHub commitment, and Linear deal-won
  traces pass the same consistency checks
- multi-state traces can accept multiple journal refs and materialized snapshots
- recent-change and context-package traces preserve routing and freshness refs

After code exists, these become automated tests.

## Implementation Order

1. Add schema validation utility.
2. Add fixture consistency tests.
3. Add file-backed stores.
4. Add fixture reviewer.
5. Add committer conversion from model output to journal/memory/commit result.
6. Add snapshot materializer.
7. Add recent-change registry writes from commit results, including affected
   state ids, source refs, candidate personas, routing reason, and relevance
   tier.
8. Add context package assembly for standing, recent-change, and opportunity
   packages.
9. Add CLI commands.
10. Replace fixture reviewer with model reviewer.
11. Add optional `paia-memory` adapter.

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

- The catch-point map is documented but not automated.
- The recent-change-entry contract is draft only.
- The context-package contract is draft only.
- Routing audit rules are draft only.
- Context package freshness and source watermark semantics are draft only.
- Package-level read permissions and redaction are not defined.
- The Linear deal-won to Laura opportunity fixture is fixture-only, not automated.
- The model reviewer prompt is not defined.
- File-backed idempotency rules are not defined.
- Promotion proposal persistence needs a pending-approval record shape.
- The `paia-memory` adapter boundary is not specified in detail.
