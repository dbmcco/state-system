# Source Events And Idempotency

Source events are the first catch point in the State System.

They represent facts observed from systems of record before the model decides
what those facts mean.

## Purpose

A source event should answer:

- what system produced the change?
- what changed?
- when did it happen?
- when did we observe it?
- who or what caused it?
- which source refs prove it?
- how can the event be deduped?
- what state objects or personas might be candidates for review?
- was the sync complete or partial?

The draft contract is `schemas/source-event.schema.json`.

## Boundary

Source events are factual envelopes.

They should not decide durable meaning or agent opportunity.

Allowed:

- Linear says deal stage changed from proposal to won.
- GitHub says PR 142 merged.
- Workgraph says task `launch-copy-review` was completed.
- Speedrift says `specdrift` produced finding `finding-123`.

Not allowed:

- This deal should become a LinkedIn post.
- This PR means the capability is launch-ready.
- This task proves the project is healthy.
- Laura should act on this.

Those are model-mediated decisions after routing and packaging.

## Idempotency

Every source event needs an idempotency key.

Preferred key order:

1. native source event id, if the source provides one
2. stable source ref plus observed field transition
3. semantic fingerprint when no reliable event id exists

Examples:

```text
linear-event-southern-abrasives-stage-won-2026-04-28
github:pr:lightforge/lfw-ai-graph-crm#142:merged@abc1234
workgraph:repo:state-system:task:launch-copy-review:done@2026-04-28T16:00:00Z
```

The same idempotency key should not create duplicate triggers, journal entries,
recent-change entries, or opportunity packages.

## Source Watermarks

Source adapters should report sync context when available:

- sync id
- cursor
- source watermark
- partial/full sync flag
- confidence

This lets the system distinguish:

- a confirmed absence of change
- a partial sync that may have missed changes
- a stale cursor
- out-of-order events

## Partial Sync Behavior

Partial source events can still become evidence, but they should carry lower
confidence.

The model can use partial evidence, but should preserve uncertainty. The
committer should be more conservative when a proposal depends on partial source
state.

## Southern Abrasives Example

The Linear event for Southern Abrasives should be represented first as a source
event:

```text
source_system: linear
source_event: deal.stage_changed
source_event_id: linear-event-southern-abrasives-stage-won-2026-04-28
change:
  object_ref: linear:deal:southern-abrasives
  field: stage
  old_value: proposal
  new_value: won
```

Only after that does the system create a trigger and ask the model whether deal
state should update.

## Design Rule

Source adapters catch facts and identity.

They do not catch meaning.

If source adapters start deciding what is important, the model-mediated boundary
has already been violated.
