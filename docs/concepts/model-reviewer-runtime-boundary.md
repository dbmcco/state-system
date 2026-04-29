# Model Reviewer Runtime Boundary

The model reviewer is the first layer allowed to decide durable meaning. It
receives a model review packet and returns a model proposal output.

The runner gathers context. The model decides interpretation. The committer
validates and persists allowed effects.

## Runtime Contract

```text
ModelReviewPacket
  -> model reviewer
  -> ModelProposalOutput
  -> committer
```

The production reviewer should be replaceable with the current
`FixtureReviewer`. Adding a real model should not change runner, committer, or
store contracts.

## Reviewer Input

The reviewer receives a payload matching
`schemas/model-review-packet.schema.json`.

Required sections:

- trigger
- evidence packet
- current state snapshots
- recent journal entries
- agent memory entries
- persona context
- governance constraints
- allowed output classes

The reviewer may use these sections to reason about relevance, salience,
uncertainty, memory, action proposals, and rollups. It should cite source refs
and state refs rather than copying large source material into proposed records.

## Reviewer Output

The reviewer must return a payload matching
`schemas/model-proposal-output.schema.json`.

Allowed decisions:

- `no_op`
- `propose_updates`
- `needs_approval`
- `needs_evidence`
- `reject`

Allowed proposal classes:

- state proposals
- memory proposals
- promotion proposals
- action proposals
- rollup requests
- missing evidence
- review signal

The reviewer can propose effects. It cannot commit them.

## Tools

The first production reviewer should be conservative about tools.

Allowed:

- inspect packet sections
- request evidence refresh or missing evidence as output
- cite known source refs, state refs, memory refs, and package refs

Not allowed in the reviewer:

- append journals
- mutate snapshots
- persist memory
- execute actions
- publish external content
- create Workgraph tasks directly
- approve its own protected action

External tool execution belongs after committer approval or in a later access
adapter.

## Code Responsibilities

Code may enforce:

- input schema validation
- output schema validation
- required ids and refs
- allowed output enum values
- fixture replay in tests
- model call retries only as transport concerns

Code must not enforce:

- what counts as marketing opportunity
- whether a PR means launch readiness
- whether a deal should become public content
- whether an agent memory is strategically important
- how to resolve business tension between agents

Those are model judgments expressed as proposals, uncertainty, missing evidence,
or no-op decisions.

## Agent Access Model

State System is not the agent runtime. It is the continuity layer shared by
multiple agent runtimes.

### PAIA Agents

PAIA agents are long-lived actors with identity, memory, and recurring work.

They should use State System through adapters:

```text
PAIA runtime
  -> request standing/recent/opportunity context package
  -> act through PAIA tools and memory
  -> emit source events, evidence refs, and model proposals
  -> State System reviews, commits, indexes, and packages
```

PAIA may keep private and operational memory in `paia-memory`. Promotion from
agent memory into shared organizational state must go through State System
review and governance.

### CLI Agents

Claude Code, Codex, and opencode are scoped worker agents. They are usually
session-bound and repo-bound rather than permanent residents.

They should use State System as follows:

```text
CLI session starts
  -> receive repo or task context package
  -> work in native CLI/runtime
  -> emit source events for commits, tests, Workgraph changes, and findings
  -> propose state updates when useful
  -> committer decides what becomes durable
```

CLI agents should not directly mutate organizational state. They can produce
evidence, source events, and proposed updates. State System preserves continuity
across otherwise disposable sessions.

### Shared Pattern

All agents follow the same state path:

```text
agent asks for context
  -> agent does work
  -> agent emits evidence or proposal
  -> model reviewer interprets
  -> committer validates and persists
  -> recent-change and package layers prepare the next context
```

This keeps PAIA, Claude Code, Codex, and opencode interoperable without building
a universal agent runtime inside State System.

## Prompt Boundary

The production reviewer prompt should say:

- You are reviewing a State System model review packet.
- Decide what changed, what did not change, and what remains uncertain.
- Distinguish source facts from interpretation.
- Return only the model proposal output schema.
- Use no-op when no durable update is warranted.
- Use missing evidence when facts are unsupported.
- Mark approval requirements for protected state, external actions, and memory
  promotion.
- Propose rollups instead of rewriting parent state directly.
- Do not execute tools or claim that an action happened.

The prompt should not encode specific business rules like "deal won means post"
or "PR merged means launch ready."

## Replay And Inspection

Reviewer outputs must be inspectable and replayable.

Minimum requirements:

- every output cites `review_packet_id`
- every proposal cites evidence refs
- missing evidence is explicit
- review signal summarizes outcome
- no-op is represented intentionally
- approval-required effects are proposals, not executed actions

This lets the committer produce an operator receipt without reconstructing model
reasoning from a raw transcript.

## Replacement Path

The current test path is:

```text
ReviewPacketBuilder
  -> FixtureReviewer
  -> fixture ModelProposalOutput
```

The production path should be:

```text
ReviewPacketBuilder
  -> ModelReviewer
  -> validated ModelProposalOutput
```

Only the reviewer implementation changes. The packet, output, stores, and
committer contracts remain stable.
