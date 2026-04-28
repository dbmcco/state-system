# Update Cadence

State changes through triggers and reviews.

Cadence determines when the lifecycle starts. It does not determine what the
state should become. The state update lifecycle is defined in
`docs/concepts/state-update-lifecycle.md`.

## Event-Driven Updates

Examples:

- meeting completed
- client replied
- task changed
- campaign metric changed
- document edited
- deal moved
- agent action completed
- mission or strategy clarified
- human or agent onboarding step completed
- operating norm changed

## Scheduled Updates

Examples:

- daily operating-picture review
- weekly rollup
- stale-state scan
- campaign review
- relationship health review
- mission/strategy coherence review
- human onboarding review
- agent onboarding review

## Model-Mediated Review

Scheduled updates should not blindly rewrite state. They should ask a model:

- what changed?
- what matters?
- what is uncertain?
- what should be watched?
- what action is warranted?
