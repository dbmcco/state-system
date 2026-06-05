# Speedrift Execution Lane

This lane turns the State System design into Workgraph execution.

The graph is intentionally pressure-test gated. Implementation tasks build
plumbing, and pressure-test tasks try to break the model before the next layer
depends on it.

## Execution Spine

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

Parallel gates:

```text
ss-contracts-fixtures
  -> ss-pressure-contracts

ss-source-idempotency
  -> ss-pressure-idempotency

ss-committer-materializer
  -> ss-pressure-governance

ss-recent-context-packaging
  -> ss-pressure-routing-freshness
```

Adjacent design tasks:

```text
ss-runner-fixture-reviewer
  -> ss-model-reviewer-boundary

ss-recent-context-packaging
  -> ss-agent-memory-adapter
```

## Step-By-Step Pressure Tests

1. Spec anchor: does the plan preserve the North Star and model/code boundary?
2. Contracts: do schemas and fixtures validate without encoding business
   judgment?
3. Source idempotency: can duplicate source events replay without duplicate
   triggers, journals, recent changes, or packages?
4. Runner/reviewer: can no-op, missing evidence, and multi-proposal reviews
   pass through the system?
5. Committer/materializer: can governance hold risky effects without
   reinterpreting the model?
6. Recent-change packaging: can Maya receive bounded opportunity context
   without scanning unrelated operations?
7. Routing/freshness/redaction: can the system avoid flooding, hidden routing,
   stale packages, and sensitive context leaks?
8. End-to-end harness: do the four fixture traces pass with provenance,
   idempotency, governance, and package boundaries intact?

## Operating Commands

```bash
wg quickstart
wg status
wg viz --all --no-tui
./.workgraph/drifts check --task ss-spec-anchor --write-log --create-followups
./.workgraph/drifts check --task ss-e2e-pressure-harness --write-log --create-followups
```

To begin execution, start the coordinator:

```bash
wg service start
```

The first lane task is `ss-spec-anchor`. If coordinator assignment is not
available, use manual Workgraph mode: run the drift check, complete the scoped
task, run the drift check again, then mark the task done.

## Current Drift Result

The root kickoff task and final end-to-end pressure harness both passed drift
checks with green scores and no findings when the lane was seeded.
