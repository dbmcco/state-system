# State System

State System is a generic model-mediated substrate for tracking organizational
state.

It defines how organizations, missions, strategies, roles, onboarding, projects,
deals, relationships, campaigns, meetings, obligations, people, and agents
maintain durable state over time. The first use case is work and organizational
operations, not PAIA migration. PAIA remains a useful reference, but this repo
owns its own design and can grow into runtime plumbing.

## Core Idea

State is not a note, a prompt, or a transient model context dump.

State is a durable, scoped record of:

- what appears to be true now
- why that view changed
- what evidence supports it
- what is uncertain
- what needs attention
- what actions have been proposed or taken

The model interprets meaning and proposes state transitions. Code validates
schemas, evidence, access policy, persistence, audit, and runtime execution.

## Initial Contents

- `docs/NORTH_STAR.md` - guiding North Star for the effort
- `docs/specs/2026-04-28-state-system-design.md` - initial system design
- `docs/concepts/` - focused concept notes
- `docs/concepts/end-state-architecture.md` - target architecture and reusable PAIA assets
- `docs/concepts/agent-memory.md` - individual agent memory and promotion to shared state
- `docs/concepts/ontology.md` - first-cut organizational state ontology
- `docs/concepts/lfw-ontology-pressure-test.md` - concrete LFW example used to test the ontology
- `docs/concepts/state-update-lifecycle.md` - trigger-to-journal-to-snapshot lifecycle
- `docs/concepts/first-deployment-mode.md` - first deployment mode for the end-state architecture
- `docs/concepts/model-pressure-test.md` - scenario pressure test for the model-mediated decision layer
- `docs/concepts/committer-and-governance.md` - how proposals become durable effects or pending/rejected signals
- `docs/concepts/first-deployment-implementation-blueprint.md` - implementation path and fixture trace for the first deployment
- `schemas/` - draft JSON schemas for state objects, journals, triggers, model review packets, model outputs, commit results, review signals, memory entries, personas, and facets
- `examples/` - example state packets and the first persona, Laura

## First Persona

Laura is the first modeled persona: a marketing agent focused on positioning,
campaign momentum, audience fit, narrative clarity, and commercially grounded
creative judgment.

Laura is not a PAIA personal assistant. She is a work agent whose personality
is expressed through professional judgment facets. She is also a test case for
how persona-mediated interpretation can maintain broader organizational state,
such as marketing narrative and mission alignment.
