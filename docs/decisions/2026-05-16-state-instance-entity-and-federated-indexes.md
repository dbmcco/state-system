# State Instance, Entity, And Federated Indexes

**Status:** Accepted
**Date:** 2026-05-16

## Decision

State System will model deployed runtime roots as **state instances** and the
thing being understood as an **entity**.

The canonical runtime unit is `StateInstance`.

Examples:

- `state_instance.sampleco`
- `state_instance.researchco`
- `state_instance.portfolio_co`
- `state_instance.plum`
- `state_instance.sample_personal`

An instance has an `instance_ref`, `kind`, `display_name`, `runtime_root`,
`primary_entity_ref`, `entity_kind`, governance refs, sensitivity defaults, and
optional federation refs.

The canonical capability declaration is `InstanceCapabilityPack`, not
`CompanyCapabilityPack`. A company is one entity kind, not the substrate shape.
Existing company capability packs may remain as a compatibility or
specialization layer, but new generic contracts must key by `instance_ref` and
`primary_entity_ref`.

Example User's personal instance will use:

```json
{
  "instance_ref": "state_instance.sample_personal",
  "primary_entity_ref": "entity.example_user",
  "entity_kind": "person",
  "runtime_root": "/path/to/personal-state"
}
```

Personal state must not be represented as a company for implementation speed.

## Why

The deployed SampleCo root proved that State System needs an inspectable runtime
root separate from the product repo. The next deployed roots include companies
and a personal "entire life" instance. Forcing all of these through
`company_ref` would leak the first deployment's ontology into the generic
substrate.

The correct abstraction separates:

- **product repo**: schemas, contracts, migrations, CLI, tests, docs
- **state instance**: deployed runtime root and operational boundary
- **entity**: the subject being understood
- **entity kind**: company, person, project, portfolio, household, research, or
  other
- **source/index surfaces**: externally owned or instance-owned retrieval
  systems

## Federated Sources And Indexes

State System instances may federate to source systems and to other State System
instances. Federation is declared through source connectors and index manifests;
it does not copy raw corpora by default.

Canonical index scopes:

- `raw_source_index`: source-owned raw corpus search, such as msgvault email,
  Folio notes, Drive documents, Linear issues, Zulip messages, or transcripts.
- `memory_index`: agent or person memory, such as agentmem or agent-memory.
- `relationship_index`: network evidence and relationship operating pictures,
  such as the personal/professional network substrate in
  `/path/to/relationship-substrate`.
- `interpreted_state_index`: State System-owned semantic index over accepted
  state objects, claims, evidence cards, journals, operating pictures,
  commitments, context packages, and activation artifacts.
- `artifact_index`: generated or working artifacts, such as workboard artifacts,
  project summaries, reports, or drafts.
- `operational_index`: operational task/event surfaces, such as Agent Runtime Workboard
  tasks, agent sessions, task logs, and handoff events.

State System owns the interpreted state index for a deployed instance. Raw
email remains owned by msgvault. Agent memory remains owned by agentmem.
Relationship evidence, identity resolution, and relationship operating pictures
remain owned by relationship-substrate. Personal state may query those sources
and promote selected evidence into accepted state, but it must not duplicate
every message, memory blob, or network record into its own vector store.

## Cross-Instance Federation

Personal `personal state` should reference work instances instead of copying their
state.

Example connector shape:

```json
{
  "id": "connector.personal.sampleco_state_system",
  "connector_type": "state_system_instance",
  "source_ref": "state-system-instance:state_instance.sampleco",
  "owner": "state_system",
  "access_mode": "read",
  "governance_refs": ["governance.sampleco.read_summary"]
}
```

This allows a personal understanding surface to include work context without
bypassing the governance of the SampleCo, ResearchCo, PortfolioCo, or Plum instances.

## Model Boundary

Code may expose source readiness, freshness, access evidence, index manifests,
gaps, provenance, governance, and sensitivity.

The model owns synthesis:

- how Example User is doing
- how a company is doing
- what matters most now
- which evidence is salient
- which open loop deserves attention
- what action should be proposed

No deterministic life score, company health score, priority heuristic, or
semantic routing rule is part of this decision.

## Production Implication

Implementation must proceed in this order:

1. Add the `StateInstance` and `InstanceCapabilityPack` contracts.
2. Preserve company capability behavior through specialization or compatibility,
   while making instance capability canonical for new work.
3. Generalize understanding surfaces and index manifests to key by
   `instance_ref`.
4. Add `state_system_instance`, `agentmem`, `agent_workboard`, and
   `relationship_substrate` connector support as declared surfaces.
5. Create `/path/to/personal-state` only after the generic
   contracts can represent it directly.
