# State System Speedrift Plan

**Date:** 2026-04-28
**Status:** Draft execution anchor
**Scope:** First local deployment of the generic State System

This document is the drift anchor for the State System Speedrift lane. It
turns the design into an implementation path while preserving the North Star:
State System is a durable organizational state layer, not a task tracker,
memory dump, CRM, or prompt convention.

## Execution Objective

Build a local, inspectable deployment that can run four comparison traces end
to end:

1. Laura campaign-audience clarification.
2. Patrick stale-contract review.
3. Patrick GitHub launch-readiness review.
4. Linear Southern Abrasives deal-won opportunity review.

The first deployment should prove the runtime shape, not finish the whole
platform. Every module should be small enough to inspect and shaped so it can
later move behind database, service, `agent-memory`, or `agent-runtime`
adapters without redesign.

## Non-Goals

- Do not build live Linear, GitHub, Workgraph, Speedrift, or agent runtime adapters yet.
- Do not turn Laura or Patrick into special-case runtime logic.
- Do not encode business salience as hardcoded rules.
- Do not skip fixture consistency in order to reach live model calls sooner.
- Do not let source systems mutate State System snapshots directly.

## Model And Code Boundary

Code owns:

- schema validation
- evidence refs and source refs
- file-backed persistence
- idempotency keys
- append-only journals
- snapshot materialization
- governance gates
- review signal and rollup plumbing
- CLI access
- deterministic fixture replay

The model owns:

- meaning
- salience
- uncertainty
- durable state interpretation
- persona-specific opportunity judgment
- memory proposals
- action proposals
- whether no durable update is warranted

Routing and packaging may use explicit metadata to build a bounded working set,
but the model decides whether that package represents a real opportunity or
requires action.

## Required Runtime Flow

For source-system changes:

```text
source event
  -> dedupe / idempotency
  -> trigger
  -> evidence packet
  -> model review packet
  -> model proposal output
  -> governance / committer
  -> journal and memory entries
  -> materialized snapshots
  -> rollup requests
  -> review signals
  -> recent-change registry
  -> persona routing
  -> context package
  -> opportunity review
  -> approval-gated action proposal or no-op
```

For non-source-system changes, the flow may begin at trigger, but the same
evidence, model review, governance, journal, snapshot, and review signal
contracts still apply.

## Implementation Phases

### Phase 1: Contracts And Fixture Consistency

Build schema loading and fixture consistency checks.

Acceptance gates:

- every JSON schema and example parses
- every first-deployment trace has resolvable ids across trigger, packet,
  model output, commit result, journal, memory, review signal, recent-change,
  and context package refs
- multi-state proposals can reference multiple accepted journal entries
- validation code does not decide business meaning

### Phase 2: File-Backed Stores

Implement local stores for state objects, source events, journals, memory,
rollups, review signals, commits, recent changes, and context packages.

Acceptance gates:

- stores support deterministic write/read/replay behavior
- duplicate record writes are handled explicitly
- runtime output lives under `state/`
- fixture files remain immutable examples under `examples/`
- store interfaces are not persona-specific

### Phase 3: Source Events And Idempotency

Implement source-event ingestion and replay protection.

Acceptance gates:

- `examples/source-linear-southern-abrasives-won.json` can be ingested
- replaying the same source event does not create duplicate triggers
- idempotency uses the source event contract before model review
- partial sync and confidence fields survive into evidence context
- source ingestion does not decide salience or action

### Phase 4: Runner And Fixture Reviewer

Implement the local Notice and Interpret test path.

Acceptance gates:

- a source event or trigger can produce a model review packet
- relevant snapshots, journals, memory, persona, and governance refs are loaded
  as factual context
- fixture reviewer can replay the four comparison traces
- no-op, missing evidence, and multi-proposal outcomes are representable
- runner code does not hardcode durable meaning

### Phase 5: Committer, Governance, And Materialization

Implement commit and propagation plumbing.

Acceptance gates:

- model proposal output is validated before effects are persisted
- accepted proposals append journal and memory entries
- snapshots materialize from accepted journal history
- rollup requests are queued, not blindly applied
- pending approval blocks external publication
- governance applies to packages and actions, not only state patches

### Phase 6: Recent-Change Registry And Context Packages

Implement recent-change indexing, persona routing metadata, freshness, routing
audit, excluded-context summaries, and package assembly.

Acceptance gates:

- recent-change entries preserve source, journal, commit, routing, and
  freshness refs
- Laura does not receive every operational task
- Laura can still receive a market-facing capability when affected state refs
  cross into her watched domains
- context packages include what was excluded and why
- stale packages cannot support external action without refresh
- sensitive relationship details are redacted or summarized according to
  governance

### Phase 7: CLI And End-To-End Harness

Expose the local system through a small CLI and run the pressure harness.

Acceptance gates:

- `state validate` runs schema and fixture consistency checks
- `state trigger <trigger-file>` can replay fixture traces
- `state recent --persona <persona-id>` and
  `state package --persona <persona-id>` reproduce Laura and Patrick views
- all four comparison traces pass end to end
- duplicate replay is idempotent
- no-op and missing evidence paths do not mutate snapshots
- governance blocks external actions

## Fixture Traces

Laura campaign-audience trace:

```text
examples/laura-campaign-audience-trigger.json
  -> examples/laura-model-review-packet.json
  -> examples/laura-model-proposal-output.json
  -> examples/laura-commit-result.json
  -> examples/marketing-campaign-audience-journal-entry.json
  -> examples/laura-agent-memory-entry.json
  -> examples/laura-review-signal.json
```

Patrick stale-contract trace:

```text
examples/patrick-stale-contract-trigger.json
  -> examples/patrick-model-review-packet.json
  -> examples/patrick-model-proposal-output.json
  -> examples/patrick-commit-result.json
  -> examples/patrick-contract-journal-entry.json
  -> examples/patrick-agent-memory-entry.json
  -> examples/patrick-review-signal.json
```

Patrick GitHub launch-readiness trace:

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

Linear Southern Abrasives opportunity trace:

```text
examples/source-linear-southern-abrasives-won.json
  -> examples/linear-southern-abrasives-won-trigger.json
  -> examples/linear-southern-abrasives-won-model-review-packet.json
  -> examples/linear-southern-abrasives-won-model-proposal-output.json
  -> examples/linear-southern-abrasives-won-commit-result.json
  -> examples/recent-linear-southern-abrasives-won.json
  -> examples/laura-southern-abrasives-opportunity-context-package.json
  -> examples/laura-southern-abrasives-opportunity-review-packet.json
  -> examples/laura-southern-abrasives-opportunity-model-output.json
  -> examples/laura-southern-abrasives-opportunity-commit-result.json
```

## Step Pressure Questions

Every task in the lane should answer these before completion:

1. Is this an end-state interface or a local-only shortcut?
2. Is business judgment being hardcoded?
3. Is provenance preserved?
4. Can a no-op pass cleanly?
5. Can pending approval avoid mutation?
6. Can the same trigger or source event be replayed without duplicate commits?
7. Can this later use `agent-memory` or `agent-runtime` without redesign?

## Workgraph Lane

The seeded Workgraph lane is:

```text
ss-spec-anchor
  -> ss-contracts-fixtures
  -> ss-file-stores
  -> ss-runner-fixture-reviewer
  -> ss-committer-materializer
  -> ss-recent-context-packaging
  -> ss-cli
  -> ss-e2e-pressure-harness
```

Pressure gates run alongside the main spine:

```text
ss-contracts-fixtures -> ss-pressure-contracts
ss-source-idempotency -> ss-pressure-idempotency
ss-committer-materializer -> ss-pressure-governance
ss-recent-context-packaging -> ss-pressure-routing-freshness
```

Adjacent boundary tasks:

```text
ss-runner-fixture-reviewer -> ss-model-reviewer-boundary
ss-recent-context-packaging -> ss-agent-memory-adapter
```

## Completion Definition

The first deployment is complete when the local CLI can replay the four fixture
traces, show accepted state changes with provenance, preserve no-op and pending
approval paths, dedupe replayed source events, assemble persona-scoped context
packages, and explain routing and freshness decisions without hiding model
judgment inside code.
