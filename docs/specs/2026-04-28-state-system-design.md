# State System Design

**Date:** 2026-04-28
**Status:** Draft
**Scope:** Generic organizational state system for model-mediated agents and human operators

## Problem

Organizations scatter current truth across chats, documents, tasks, meetings,
CRM records, calendars, memory stores, decisions, onboarding rituals, operating
principles, and individual agent context. Agents can retrieve pieces of that
history, but they do not necessarily know the current state of a mission,
strategy, role, human onboarding process, agent onboarding process, project,
deal, relationship, campaign, obligation, or operating picture.

The missing layer is a durable state system: a way to represent what appears to
be true now, why it changed, what evidence supports it, what is uncertain, and
what should happen next.

## Goal

Create a generic state system that starts as a design and schema repo and can
grow into runtime plumbing.

The system should support:

- scoped state objects for organizational and work entities
- append-only state journals
- materialized snapshots
- explicit triggers and review signals
- individual agent memory entries
- rollups from child state to parent state
- persona and facet definitions for model-mediated agents
- regular state updates from meetings, messages, tasks, tool results, and model reasoning
- evidence and provenance requirements
- model-mediated interpretation with code-enforced safety and integrity

## Non-Goals

- Do not migrate PAIA directly into this repo.
- Do not create a one-file global state dump.
- Do not encode business judgment as hardcoded thresholds or routing rules.
- Do not require every state update to be manually authored.
- Do not build runtime services before the core contracts are clear.

## Core Concepts

The detailed state-family ontology lives in
`docs/concepts/ontology.md`. Ontology comes before lifecycle and infrastructure:
the system should know what kinds of state exist before it defines how they
change or where they are stored.

The end-state architecture lives in
`docs/concepts/end-state-architecture.md`. Early runtime work should implement
the target interfaces in a small deployment mode, not create a throwaway local
architecture.

### StateObject

A `StateObject` is a scoped current-state view.

Examples:

- project
- deal
- client
- relationship
- campaign
- meeting
- obligation
- person
- organization
- mission
- strategy
- principle
- role
- onboarding
- norm
- decision area
- capability
- agent
- operating picture

Each state object owns a local truth. Parent rollups synthesize child state but
do not replace it.

### StateJournalEntry

A `StateJournalEntry` is an append-only record of why state changed.

It records:

- source trigger
- prior state reference
- proposed patch
- model interpretation
- evidence references
- uncertainty
- actions proposed or taken
- actor or agent responsible

Journal entries are the audit trail. Snapshots are the readable current view.

### Snapshot

A snapshot is the materialized state of a `StateObject` at a point in time.
Agents should usually read snapshots first, then inspect journal history when
they need provenance or nuance.

### Persona

A persona defines an agent's professional identity and interpretive lens.

It includes:

- role
- mission
- facets
- communication posture
- authority boundaries
- watched state domains
- allowed actions
- anti-facets

Personality is not decorative. It changes what the agent notices and how it
interprets state.

### Agent Memory

Agent memory is what an individual agent has learned over time.

It is distinct from persona and distinct from shared organizational state.
Personas define who an agent is. Agent memory records what the agent has learned.
Organizational state records shared current truth.

Agent memory should support promotion into shared state when observations become
important, evidenced, and approved. See `docs/concepts/agent-memory.md`.

### Facet

A facet is a specific judgment tendency or behavioral lens.

For example, Laura's marketing facets include:

- notices audience-message mismatch
- protects narrative clarity
- converts vague campaign intent into testable positioning
- distinguishes creative possibility from commercial priority
- escalates when brand, audience, or offer coherence is weak

## Model-Mediated Boundary

The model decides:

- what a situation means
- what changed
- what evidence matters
- which uncertainties are important
- what next actions make sense
- how a persona's facets should affect interpretation
- what an agent should remember
- whether agent memory should be proposed for shared-state promotion
- whether a state object should roll up into a broader concern

Code decides:

- whether JSON parses against schema
- whether referenced evidence exists
- whether the actor may read or write the state object
- whether requested actions are allowed
- whether a snapshot can be materialized
- whether the journal entry is persisted
- whether a memory write is allowed
- whether a promotion requires approval
- whether audit and replay are possible

Code should not decide business salience through brittle thresholds like
"if three updates happened, escalate." The model should interpret salience from
state, evidence, context, and persona.

## Update Flow

The detailed lifecycle lives in
`docs/concepts/state-update-lifecycle.md`. The durable invariant is journal
first, snapshot second.

1. A trigger arrives: meeting note, message, task update, tool result, scheduled review, human edit, or agent reasoning cycle.
2. The system loads relevant snapshots and recent journal entries.
3. The model receives the trigger, evidence, persona, and state context.
4. The model proposes observations, state patches, uncertainties, and actions.
5. Code validates schema, evidence, access, and action boundaries.
6. The system appends a journal entry.
7. The system materializes an updated snapshot.
8. Parent rollups are queued or recomputed when affected.

The draft trigger and review-signal contracts live in
`schemas/trigger.schema.json` and `schemas/review-signal.schema.json`.
The model-mediated review contracts live in
`schemas/model-review-packet.schema.json` and
`schemas/model-proposal-output.schema.json`.
The committer receipt contract lives in `schemas/commit-result.schema.json`.

## Regular Updates

State should update through both event-driven and scheduled paths.

Event-driven updates:

- meeting completed
- client replied
- task status changed
- deal stage changed
- document edited
- campaign metric changed
- agent action completed

Scheduled updates:

- daily operating-picture review
- weekly project/deal rollup
- stale-state detection
- persona-specific review, such as Laura scanning campaigns for unclear positioning

The scheduled path should ask the model what changed or what needs attention.
It should not blindly rewrite all snapshots.

## Rollups

Rollups are synthesized views over child state.

Examples:

- campaign state rolls into marketing operating picture
- deal state rolls into revenue pipeline
- relationship state rolls into account health
- project state rolls into delivery operating picture

Rollups must preserve references to child state and journal evidence. They
should not become manually maintained mega-docs.

## First Persona: Laura

Laura is the first modeled persona.

Laura is a marketing agent. Her role is to track and improve the state of
positioning, audience fit, campaign momentum, message clarity, and marketing
execution. She also helps maintain marketing narrative state and flags tension
between campaign work and the broader mission, strategy, or organizational
voice.

Laura should notice:

- unclear audience
- weak offer framing
- inconsistency between campaign goal and creative direction
- missing proof points
- stale launch plans
- relationship between market signal and current messaging
- when creative exploration is useful and when commercial focus is needed

Laura should avoid:

- generic marketing language
- chasing novelty without evidence
- over-polishing before the offer is clear
- treating vanity metrics as success without business context

## Initial Repo Phases

### Phase 1: Design and Contracts

Create docs, schemas, and examples for state objects, journals, personas, and facets.

This phase must preserve the North Star: state covers organizational condition,
not only tactical work status.

### Phase 2: First Deployment Mode

Add a small deployment of the end-state interfaces that can validate schemas,
append journal entries, materialize snapshots, persist agent memory, and compute
simple rollup requests.

The first deployment mode should remain local and inspectable at first, while
preserving the target interfaces: evidence store, memory store, state store,
model reviewer, governance, committer, and access surface. See
`docs/concepts/first-deployment-mode.md`.

### Phase 3: Model-Mediated Update Runner

Add a runner that gives a model a trigger, state context, persona, and tools,
then validates and persists the resulting state transition.

### Phase 4: Work Integrations

Connect to real work sources such as notes, calendar, tasks, CRM, docs, and
campaign metrics.

## Open Questions

- Which storage backend should be first: local files, SQLite, Postgres, or a memory service?
- Should snapshots be directly editable by humans, or should human edits always append journal entries?
- How strict should evidence requirements be for internal interpretations versus external factual claims?
- How should personas inherit shared organizational policy without becoming generic?
- What trigger and review-signal schemas are needed to prove the model-mediated
  update loop?
- Which organizational state types need first-class treatment versus generic
  `StateObject` specialization?
