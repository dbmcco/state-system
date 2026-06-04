# End-State Architecture

State System should be built toward its end state from the beginning.

Early local execution can be useful, but it should be a deployment adapter for
the target architecture, not a temporary architecture that later gets replaced.

## End-State Purpose

State System is a shared organizational state and agent memory substrate.

It answers:

- what appears to be true now?
- why do we think that?
- what changed?
- what remains uncertain?
- what did an agent learn?
- what can become shared organizational truth?
- what requires approval before action or promotion?

## Target Layers

```text
source systems
  -> evidence layer
  -> memory kernel
  -> state kernel
  -> context packaging layer
  -> model-mediated update layer
  -> governance layer
  -> access surfaces
```

These layers can run locally, in a database-backed service, or through existing
agent runtime platform services. The layer boundaries matter more than the first
deployment shape.

## 1. Source Systems

Source systems remain the systems of record for raw facts and artifacts.

Examples:

- Workgraph
- Speedrift / Driftdriver
- Linear
- GitHub
- Google Drive
- email
- calendar
- CRM
- meeting notes
- campaign metrics
- human edits
- agent actions

GitHub should be treated carefully. Commits, pull requests, issues, review
comments, checks, and releases are source records. Some of those records may
also contain commitments, such as promised follow-up work, launch requirements,
review conditions, or governance approvals. The raw GitHub artifact belongs in
the evidence layer; the interpreted commitment belongs in state only after model
review and governance checks.

State System should reference source records rather than copying large blobs
into state objects.

## 2. Evidence Layer

The evidence layer stores and retrieves source-backed records.

End-state responsibilities:

- evidence ledger
- deduplication
- source references
- provenance metadata
- embeddings
- semantic retrieval
- digests and summaries
- active context sections

Known reusable implementation:

- `/path/to/agent-memory`

`agent-memory` already owns memory store, context retrieval, embedding interface,
knowledge persistence, evidence, facets, triplets, digests, and active context.
State System should reuse or adapt those capabilities instead of rebuilding them.

## 3. Memory Kernel

The memory kernel stores what agents and organizations have learned.

It includes:

- agent-specific memories
- identity and professional facets
- learned preferences
- recurring patterns
- domain observations
- working theories
- digests
- semantic recall
- promotion candidates

Memory is not the same as state. Memory is accumulated learning and recall.
State is the current interpreted view that should guide action.

## 4. State Kernel

The state kernel stores durable current truth.

End-state responsibilities:

- state object registry
- append-only state journals
- materialized snapshots
- state family and trait metadata
- parent/child state references
- rollup queue
- review signals
- replay and audit

This repo currently defines the generic state object and journal contracts. The
end state may implement those contracts in a database, but local file-backed
execution should use the same abstractions.

## 5. Context Packaging Layer

The context packaging layer prepares bounded working sets for agents and model
reviews.

End-state responsibilities:

- persona-specific standing packages
- recent-change packages
- opportunity review packages
- relevant state, journal, memory, evidence, and governance slices
- excluded-context summaries
- package ids for audit and replay

The package is not the decision. It gives the model the right context and
available actions without forcing the agent to search the whole organization.

## 6. Model-Mediated Update Layer

The update layer gives models tools and context, then asks them to decide what
changed.

The model decides:

- relevance
- salience
- fact versus interpretation
- uncertainty
- state patches
- memory writes
- rollup requests
- proposed actions
- promotion from private memory to shared state

Code executes:

- schema validation
- evidence checks
- persistence
- permissions
- approval gates
- action execution
- audit events

Known reusable implementation:

- `/path/to/agent-runtime`

`agent-runtime` already has a model-mediated agent state loop with
evaluation, risk checks, action execution, journals, snapshots, events, and
memory writes. State System should learn from that implementation and generalize
the pattern beyond agent runtime agents.

## 7. Governance Layer

The governance layer controls what can become durable state or action.

It covers:

- actor authority
- read/write permissions
- approval boundaries
- risk classes
- protected state
- external communication rules
- promotion from agent memory to organizational state
- audit and replay requirements

Governance should not decide business meaning. It should decide whether a
model-proposed state transition, memory write, action, or promotion is allowed.

## 8. Access Surfaces

The same kernel should support multiple access surfaces.

Examples:

- CLI
- API
- MCP tools
- agent runtime tools
- lightweight human UI
- scheduled review jobs
- integration workers

The first surface can be CLI, but the architecture should assume API/tool access
as the long-term default for agents.

## Existing agent runtime Assets To Leverage

### `agent-memory`

Useful for:

- evidence ledger
- facets
- triplets
- digests
- embeddings
- semantic retrieval
- active context
- tenant isolation

### `agent-runtime`

Useful for:

- model-mediated state loop
- state evaluator protocol
- action/risk model
- journal and snapshot flow
- file-backed and in-memory store patterns
- event publishing

### `agent-runtime-contracts`

Useful for:

- typed agent state contracts
- actions
- approval states
- evidence and context atoms

### `agent-runtime-agents`

Useful for:

- named agent memory patterns
- Derek's architectural memory staging and promotion pattern
- Samantha's identity/facet and conversational continuity patterns

## Architectural Direction

Build toward:

- shared organizational state
- individual agent memory
- explicit promotion paths
- reusable memory backend
- model-mediated state updates
- governed persistence
- multiple deployment adapters

Do not build toward:

- each agent keeping isolated private memory only
- prompt-only state
- hand-maintained rollup documents
- direct snapshot mutation from integrations
- hardcoded business judgment
- a local-only runtime that must be replaced later

## First Deployment Mode

The first deployment mode can still be local and inspectable, but it should use
the same interfaces:

- evidence store interface
- memory store interface
- state store interface
- model reviewer interface
- governance interface
- access surface interface

That lets local files prove the architecture without becoming a cul-de-sac.
