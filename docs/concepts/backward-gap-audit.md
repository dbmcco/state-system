# Backward Gap Audit

This audit works backward from the end-state system before implementing the
committer. Its purpose is to prevent two opposite failures:

- building the committer before it knows which constraints it must enforce
- overbuilding new subsystems before fixture-backed usage proves they are needed

The near-term rule is:

```text
only block committer on constraints it must enforce to preserve safety,
idempotency, provenance, and auditability
```

## Blocks Committer Now

These items must be represented in the committer implementation or its immediate
contracts.

### Approval And Pending Effects

The committer needs a durable way to represent proposals that are valid but not
allowed to mutate protected state or execute risky actions yet.

Minimum now:

- commit results record `pending_approvals`
- protected external actions do not execute
- protected state is not mutated while approval is pending
- review signals can say `pending_approval`

Not now:

- approver workflow
- notification delivery
- approval expiration automation
- human UI

### Evidence Resolution

The committer needs to distinguish unsupported proposals from supported
proposals. It should not decide meaning, but it must check that proposed effects
cite evidence refs available in the review packet or stores.

Minimum now:

- accepted journal and memory proposals cite evidence refs
- missing evidence produces rejected or pending outcomes, not fabricated state
- unresolved evidence remains visible in commit results or review signals

Not now:

- semantic evidence search
- canonical-source ranking
- embedding-backed retrieval

### High-Risk Freshness

The committer should block external or protected effects when the proposal
depends on stale or missing package/governance context.

Minimum now:

- internal low-risk updates may proceed with uncertainty recorded
- external publication and protected actions require fresh approval context
- stale context can produce pending approval or refresh-required review signals

Not now:

- full package invalidation service
- scheduled freshness sweeps
- UI-level refresh prompts

## Already Covered By Existing Tasks

These are real concerns, but the current graph already has a place for them.

- Source event replay and duplicate detection: covered by
  `ss-pressure-idempotency`.
- Runner and fixture reviewer boundary: covered by `ss-runner-fixture-reviewer`.
- Recent-change routing and package redaction: covered by
  `ss-recent-context-packaging` and `ss-pressure-routing-freshness`.
- CLI inspection: covered by `ss-cli`.
- Optional `agent-memory` boundary: covered by `ss-agent-memory-adapter`.

## Follow-Up Later

These should not block committer implementation, but they should be pressure
tested before end-to-end confidence.

### Conflict Semantics

Laura and Patrick can disagree about the same underlying change. For now,
uncertainty, pending approval, and separate review signals are enough. Later,
conflict records may be useful if coordination becomes hard to inspect.

### Rollup Debt

Queued rollups can fall behind, making parent operating pictures stale. For now,
the committer should queue rollups and expose the refs. Later, recent-change and
package work should represent overdue rollups and stale parent summaries.

### Routing Miss Audit

Hidden routing is a serious risk, but it belongs with recent-change and package
work. The committer should not solve routing. It should preserve the refs and
signals that make routing auditable later.

## Defer Until Real Usage

These are intentionally deferred.

- memory confidence decay
- schema migration framework
- approval notification workflow
- full evidence search or ranking
- package cache invalidation service
- human-facing approval UI

## Operational Note

Workgraph auto-spawn attempts have repeatedly created dead worker state in this
repo. That is an execution-lane issue, not State System product behavior. Until
the lane is fixed, State System work should proceed manually and normalize
`.workgraph/graph.jsonl` before committing.

## Decision

Proceed to `ss-model-reviewer-boundary` and `ss-committer-materializer` with a
narrow committer scope:

- validate model output shape
- check evidence refs
- enforce approval/pending behavior for protected effects
- append accepted journals and memory records
- materialize snapshots from accepted journals
- queue rollups
- emit commit results and review signals

Do not add conflict records, approval workflows, package invalidation services,
or evidence search in the committer task.
