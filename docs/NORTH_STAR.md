# North Star

State System is an organizational state layer.

It tracks the living condition of an organization, its work, its people, its
agents, its mission, its roles, its decisions, and its evolving understanding of
the world.

State is not absolute truth. It is durable working interpretation: what appears
to be true now, why we believe it, what evidence supports it, what remains
uncertain, and what action may be warranted.

The system turns scattered signals from meetings, messages, documents, tasks,
metrics, decisions, rituals, onboarding, and agent reasoning into scoped state
objects, append-only journals, current snapshots, and rollups that humans and
agents can act from.

## What State Covers

State includes tactical work:

- projects
- deals
- campaigns
- relationships
- meetings
- obligations
- next actions

State also includes institutional context:

- mission
- strategy
- operating principles
- roles
- norms
- onboarding
- decision history
- organizational narrative

State includes developmental context:

- a human ramping into a role
- an agent learning its responsibilities
- a team clarifying how it works
- a process maturing from ad hoc to reliable
- a market belief becoming stronger, weaker, or stale

## Personas

Personas are first-class.

A persona is not a prompt style. It is an interpretive lens with responsibilities,
facets, watched domains, authority boundaries, and anti-patterns.

Laura, as a marketing agent, should notice different things in the same state
than an operations, finance, delivery, onboarding, or strategy agent would.

Personality matters only when it changes professional judgment: what the agent
notices, how it interprets ambiguity, when it escalates, and what it proposes.

## Model And Code Boundary

The model owns interpretation:

- what changed
- what matters
- what is uncertain
- what should be watched
- what actions make sense
- how persona facets affect the reading of state

Code owns integrity:

- schemas
- evidence references
- permissions
- persistence
- auditability
- replay
- safe execution boundaries

The system should not encode organizational judgment as brittle thresholds or
routing rules. It should provide the structure that lets models interpret state
while code keeps the record grounded and inspectable.

## Success

State System succeeds when a human or agent can ask:

```text
What is the current state of this organization, workstream, role, person, agent,
project, campaign, relationship, decision, or mission?

Why is that the state?
What changed recently?
What evidence supports it?
What remains uncertain?
Who or what is responsible?
What should happen next?
How does this affect the broader organization?
```

And receive an answer that is current, grounded, scoped, inspectable, and shaped
by the right persona.

State System is not a task tracker, CRM, notes app, memory store, onboarding app,
or agent framework by itself. It is the missing state layer between those systems:
the layer that helps an organization remain understandable, current, and
actionable over time.

