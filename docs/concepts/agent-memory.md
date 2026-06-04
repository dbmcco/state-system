# Agent Memory

Agents need their own memory.

Shared organizational state is not enough. A useful agent must also carry what
it has learned from its own work, mistakes, observations, and repeated
interactions.

## Memory Is Not Persona

Persona defines professional identity.

Examples:

- role
- mission
- watched domains
- facets
- authority boundaries
- communication posture
- anti-patterns

Memory defines learned experience.

Examples:

- preferences learned from Example User
- successful tactics
- repeated failure modes
- domain observations
- relationship-specific context
- tool fluency
- working theories
- lessons from prior reviews
- patterns noticed across projects

An agent can keep the same persona while its memory evolves.

## Memory Is Not Organizational State

Organizational state is shared current truth.

Examples:

- mission
- strategy
- campaign state
- project state
- operating picture
- governance rules
- onboarding state

Agent memory is individual learning.

Example:

Laura may learn that SampleCo messaging becomes stronger when it frames
AI work as bounded business capability rather than generic AI application
development. That is initially Laura's learned memory. It becomes organizational
state only if it is promoted, evidenced, and accepted.

## Memory Planes

```text
evidence records
  -> agent memory
  -> agent state
  -> organizational state
```

These planes overlap, but they should not collapse into one blob.

### Evidence Records

Raw or source-backed records.

Examples:

- conversations
- meetings
- documents
- task events
- campaign metrics
- source links

### Agent Memory

The agent's learned recall.

Examples:

- `marketing.draft.positioning.bounded-capability-language`
- `marketing.pattern.audience-proof-before-copy`
- `relationship.example_user.prefers-direct-strategy-language`

### Agent State

The agent's current operating condition.

Examples:

- active situations
- goals
- plans
- open questions
- next actions
- current confidence
- memory refs being used

### Organizational State

Shared current truth that other humans and agents can rely on.

Examples:

- marketing narrative state
- mission state
- strategy state
- operating picture
- campaign state

## Memory Lifecycle

```text
experience
  -> memory proposal
  -> memory write
  -> memory review
  -> durable agent memory
  -> optional promotion proposal
  -> shared state update
```

Not every experience should become memory. Not every memory should become
shared state.

## Draft And Promotion Pattern

The Derek memory model in `/path/to/agent-runtime-agents`
uses a useful pattern:

```text
arch.draft.*
  -> reviewed and consolidated
  -> arch.*
```

State System should generalize that pattern.

For Laura:

```text
marketing.draft.positioning.bounded-capability-language
  -> reviewed and consolidated
  -> marketing.pattern.bounded-capability-language
  -> optional promotion to state.sampleco.marketing_narrative
```

The draft layer lets agents learn without immediately converting observations
into shared truth.

## Promotion Rules

Agent memory can propose promotion into organizational state when:

- the memory is recurring or high-signal
- evidence references exist
- the agent can explain why it matters
- the target state object is clear
- governance allows the proposal
- required human approval is satisfied

Promotion should create a state journal entry. It should not silently mutate a
snapshot.

## Relationship To Agent Runtime Memory

`agent-memory` already has useful primitives:

- evidence ledger
- facets
- facet layers
- semantic retrieval
- triplets
- digests
- active context sections
- tenant isolation

State System should treat those as implementation candidates for agent memory.
The generic architecture should not require agent runtime, but it should not ignore a
working memory substrate that already exists.

## Contract

The draft generic schema for one memory entry is
`schemas/agent-memory-entry.schema.json`.

It intentionally resembles the useful parts of `agent-memory` facets while
adding promotion fields needed by State System:

- `agent_ref`
- `memory_key`
- `layer`
- `memory_type`
- `confidence`
- `evidence_refs`
- `related_state_refs`
- `promotion_status`
- `promotion_target_ref`
- `status`
- `supersedes_ref`
- `superseded_by_ref`
- `last_reviewed_at`

## Laura Memory Examples

Candidate Laura memory families:

- `identity.*`: durable Laura self-model and professional posture
- `marketing.pattern.*`: campaign and positioning patterns
- `marketing.draft.*`: unreviewed observations
- `relationship.*`: collaborator-specific communication context
- `sampleco.narrative.*`: learned SampleCo narrative patterns
- `tooling.*`: learned tool capabilities and limitations

Examples:

```text
marketing.draft.audience-before-copy:
Laura has repeatedly found campaign work weaker when copy starts before audience
and proof are defined.
```

```text
relationship.example_user.directness:
Example User tends to prefer direct strategic language over polished marketing
abstraction when evaluating positioning.
```

```text
sampleco.narrative.bounded-business-capability:
SampleCo messaging appears stronger when framed as bounded business capability rather
than generic AI app development.
```

## Design Rule

Agent memory should be private enough to preserve individual learning, but
governed enough that important learned truth can be promoted into shared state.

The promotion path is the bridge between individual agent intelligence and
organizational learning.
