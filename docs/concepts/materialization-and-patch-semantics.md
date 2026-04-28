# Materialization And Patch Semantics

Materialization turns accepted journal history into a readable current snapshot.

The materializer is mechanical. It should not reinterpret business meaning or
invent new conclusions. It applies accepted journal entries in order and keeps
the snapshot aligned with provenance.

## Core Rule

Snapshots are derived.

Do not edit a snapshot directly. A snapshot changes because a journal entry was
accepted, then materialized.

## Patch Shape

`state_patch` is a partial object patch against a state snapshot.

Initial semantics:

- scalar fields replace prior scalar values
- arrays replace prior arrays unless the field has merge semantics
- objects replace prior objects unless the field has merge semantics
- unknown fields are rejected by schema validation
- protected fields cannot be patched directly

This keeps first implementation simple and auditable.

## Protected Fields

These fields are controlled by the materializer or object identity:

- `id`
- `type`
- `primary_family`
- `secondary_families`
- `state_traits`
- `scope`
- `as_of`
- `latest_journal_entry_id`

Changing these should require a higher-level migration or governance-approved
state reclassification, not a normal model patch.

## Materializer-Controlled Updates

After applying `state_patch`, the materializer updates:

- `as_of` to journal `created_at`
- `latest_journal_entry_id` to journal `id`
- `evidence_refs` to include journal `id` and journal evidence refs

It may also preserve existing `parent_state_refs` and `child_state_refs` unless
the accepted patch explicitly changes them and governance allows that change.

## Array Semantics

Default array behavior is replacement.

Examples:

- `open_questions` replacement means the model has re-evaluated the active open
  questions.
- `goals` replacement means the model has re-evaluated current goals.
- `next_actions` replacement means the model has re-evaluated active proposed
  actions.

Append semantics should be explicit later if needed. Hidden append behavior
makes replay harder to reason about.

## Evidence Refs

The snapshot should keep evidence visible without becoming an evidence store.

Initial rule:

1. Start with existing snapshot `evidence_refs`.
2. Add the accepted journal entry id.
3. Add the journal entry `evidence_refs`.
4. Deduplicate while preserving order.

## Rollup Requests

Rollup requests in a journal entry do not mutate parent snapshots directly.

They are queued for a separate rollup review.

## Rejected Or Pending Patches

Rejected and pending proposals are not materialized.

Pending approval may produce a commit result and review signal, but it should not
change the target snapshot until approved and committed.

## Replay

Given:

- an initial state object
- an ordered list of accepted journal entries

the materializer should be able to regenerate the same current snapshot.

If compaction or materialization logic improves later, replay can regenerate
snapshots without changing the journal.

## Laura Pressure Test

Input snapshot:

- `examples/marketing-campaign-state.json`

Accepted journal:

- `examples/marketing-campaign-audience-journal-entry.json`

Expected materialized snapshot:

- `examples/marketing-campaign-state-after-audience.json`

Pressure-test result:

- `summary` is replaced by the journal patch
- `open_questions` is replaced by the journal patch
- `as_of` is updated to journal `created_at`
- `latest_journal_entry_id` is updated to journal `id`
- `evidence_refs` includes both journal refs
- parent refs remain unchanged
- rollup request is not copied into the child snapshot

## Future Questions

- Do we need JSON Patch or merge-patch semantics later?
- Should state patches include explicit operations for append/remove?
- Should protected-field changes become a distinct `reclassification` update
  class?
- Should evidence refs be separated into direct and inherited evidence?
