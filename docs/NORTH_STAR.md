# North Star

State System is an organizational state layer.

It tracks the living condition of an organization, its work, its people, its
agents, its mission, its roles, its decisions, and its evolving understanding of
the world.

State is not absolute truth. It is durable working interpretation: what appears
to be true now, why we believe it, what evidence supports it, what remains
uncertain, and what action may be warranted.

State System has two separable forms:

- the **State System product repo**, which defines schemas, contracts, runtime
  code, migrations, and documentation
- a **deployed State System instance**, such as
  `/path/to/state-system-runtime`, which holds a company's
  actual runtime state, read models, freshness evidence, index manifests,
  database configuration, and operational artifacts

The product repo should not contain private company corpora or mutable runtime
indexes. A deployed company instance should own the runtime substrate needed to
make that company understandable, including database/vector-index configuration
and State System-owned semantic indexes as they become operational.

Different deployed instances may need different source surfaces. A personal
instance can declare health, activity, media, or other personal source-owned
systems such as Garmin Connect or Spotify; a company instance should not inherit
those as defaults. Source-specific connectors are admissible only as explicit
capability-pack declarations with preflight, freshness, index ownership, and
governance status visible before any model treats them as usable evidence.
Personal relationship indexes follow the same rule. A company instance such as
SampleCo may use Example User's long-history relationship evidence only through an
explicit governed federated query route; it must not copy raw personal
relationship records or silently treat personal sources as company sources.

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

The first ontology is captured in `docs/concepts/ontology.md`. It groups state
into organizational identity, operating, work, relationship, knowledge, role and
persona, onboarding, and governance families.

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

Semantic retrieval is part of the integrity layer when it retrieves explicit
State System records, evidence cards, claims, memory, journals, and operating
pictures with provenance. Retrieval must remain evidence plumbing, not hidden
organizational judgment. Source systems may still own raw corpus indexes, while
State System instances own the canonical interpreted-state index and federate to
source indexes when drill-down is needed.

See
`docs/decisions/2026-05-16-runtime-instance-and-vector-ownership.md` and
`docs/decisions/2026-05-16-state-instance-entity-and-federated-indexes.md` for
the current decision records.

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

The product repo now exposes a deterministic read surface for this question set:

```bash
python3 -m state_system.cli --project-root . north-star-answer \
  --query "What is the current state?" \
  --package personal=examples/instance-agent-package/instance-agent-package-sample-personal-samantha.json \
  --output-dir /tmp/state-system-north-star
```

The generated `north-star-answer.json` is not the model's final prose answer.
It is the grounded substrate a model or UI can use to answer the North Star
questions: current state, why, recent changes, evidence, uncertainty,
responsibility, next actions, and broader federation effects. It preserves the
product/instance boundary by summarizing package evidence and gaps without
copying raw source corpora or authorizing execution.

For a deterministic human-readable view of the same substrate:

```bash
python3 -m state_system.cli --project-root . north-star-answer-render \
  /tmp/state-system-north-star/north-star-answer.json \
  --check \
  --output-path /tmp/state-system-north-star/north-star-answer.txt
```

`--check` validates the JSON schema and renderer invariants before writing text.
The renderer does not fetch sources, authorize actions, or hide uncertainty.

State System is not a task tracker, CRM, notes app, memory store, onboarding app,
or agent framework by itself. It is the missing state layer between those systems:
the layer that helps an organization remain understandable, current, and
actionable over time.
