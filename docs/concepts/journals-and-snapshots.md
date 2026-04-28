# Journals And Snapshots

The journal is truth. The snapshot is the current readable view.

## Journal

A journal entry records a state transition:

- what triggered it
- what class of update it is
- what changed
- what evidence was used
- what the model interpreted
- what actions were proposed or taken
- what remains uncertain

Journal entries are append-only.

## Snapshot

A snapshot is materialized from journal history. It gives agents and humans a
compact answer to "what is true now?"

Snapshots can be regenerated from journals when compaction logic improves.

## Rule

Do not update a snapshot without a corresponding journal entry.

See `docs/concepts/state-update-lifecycle.md` for the full path from trigger to
journal append, snapshot materialization, rollup review, and review signal.
