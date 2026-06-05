# Operationally Trustworthy Federated State Model

Date: 2026-05-18

## Objective

Move State System from "contract-compatible package artifacts exist" to an
operational model that a fresh agent or open-source adopter can run repeatedly:
declare sources, prove readiness, scaffold instances, federate across
instances, expose gaps, and answer real questions without private prompt
knowledge.

The target surface is the CLI-ready agent-facing package layer. The model is
done when the package and its rendered output are enough for a capable agent to
know what it can use, what it cannot use, why, and how to repair missing
coverage.

## Core Model

State System now has five layers:

1. **Product contracts**
   Schemas, examples, CLI commands, validators, and docs in the generic
   `state-system` repo.

2. **Source modules**
   Explicit declarations of source-owned systems such as msgvault, Knowledge Store,
   Relationship Substrate, Garmin Connect, Spotify, Drive, GitHub, Linear,
   docs, and local paths. A source module owns access, freshness, index
   manifests, record kinds, safe output policy, and read/write/correction
   surfaces.

3. **Deployed instance roots**
   Runtime state roots such as personal state, SampleCo, PortfolioCo, and ResearchCo. These own
   actual package artifacts, preflight records, freshness evidence, readiness
   records, local indexes, gap records, and repo-local agent guidance.

4. **Agent packages**
   Typed read models for CLI agents. A package exposes source readiness,
   freshness, gaps, route contracts, tool actions, governance boundaries,
   materialization policy, and answer behavior.

5. **Federation packs**
   A typed declaration that one instance can query another instance or source
   substrate without copying raw data. Federation packs are the boundary object
   for personal state to SampleCo, SampleCo to personal Relationship Substrate, and future
   portfolio-level state across PortfolioCo and ResearchCo.

## Source Lifecycle

Every connector or source module should move through a visible lifecycle:

| Stage | Meaning | Required Artifact |
| --- | --- | --- |
| `declared` | The module exists as a possibility. | `SourceModuleSpec` entry and instance source declaration. |
| `preflighted` | Access was checked or explicitly failed. | preflight record with `checked_at`, credential/access status, and evidence refs. |
| `freshness_proven` | Recency is known. | freshness record with `source_watermark`, `stale_after`, and gap refs if stale. |
| `indexed` | Query/read surfaces are known. | index manifest with record kinds, query surface, and raw-corpus policy. |
| `package_bound` | Agent package exposes the module. | package `source_readiness` with module refs, mode, statuses, and gap behavior. |
| `route_bound` | Routes can depend on the module safely. | `QuestionRouteContract` fields for coverage, tools, fallback, answer policy, and gap behavior. |
| `pressure_tested` | Real question behavior was tested. | pressure fixture/report proving the agent names gaps and respects boundaries. |

No source should skip from `declared` to "usable" through prompt language.

## Federation Pack Contract

A federation pack is not a raw data sync. It is a governed query contract.

Each pack should declare:

- `federation_pack_ref`
- `local_instance_ref`
- `remote_instance_ref` or `source_instance_ref`
- `federation_mode`: `instance_read`, `federated_query`, `source_substrate_query`,
  or `portfolio_rollup`
- `route_refs`
- `query_surface_refs`
- `tool_action_refs`
- `source_module_refs`
- `identity_boundary`: how people, companies, projects, and subjects are named
  across instances
- `materialization_policy`: normally `local_materialization=false` unless a
  specific governed summary artifact is permitted
- `freshness_policy`: checked_at, source_watermark, stale_after, gap refs
- `subject_note_policy`: correction notes can demote or explain context but
  must not become hidden broad filters
- `output_policy`: safe summary, evidence refs, and raw-corpus prohibition
- `repair_policy`: what the agent says or does when the remote/source route is
  missing or stale

Federation packs should be generated into deployed instances and represented in
open-source examples using synthetic refs.

## Connector Module Kit

Open-source users need a repeatable way to add a connector. The product repo
should provide a connector module kit with:

- source module schema and example
- tool action contract schema and example
- route contract schema when the connector supports question routes
- preflight result shape
- freshness result shape
- index manifest shape
- raw-corpus and safe-output policy checklist
- package rendering expectations
- tests proving package visibility and no silent readiness promotion

Spotify, Garmin Connect, and Relationship Substrate are the stress tests:

- Spotify proves historical cache vs live API modes, credential failure, cache
  bounds, and stale freshness.
- Garmin proves governed local sync and health/activity output policy.
- Relationship Substrate proves source-owned people/company records,
  subject-note correction writes, and federated no-materialization use.

## Operational Question Pressure Tests

The package layer should be tested against real questions:

- Sam: "Do I have any relationship follow-up threads I should take action on?"
- Sam: "Who do I know at smaller consulting or advisory firms?"
- Sam: "What does Spotify show recently, and is that current?"
- Iris: "What SampleCo relationship or BD follow-ups need attention?"
- Iris: "What is Iris missing because Linear, GitHub, or transcripts
  are stale?"
- Helena/Scout: "What can this agent know about the company today, and what is
  still only declared?"

The expected behavior is not a fixed answer. The expected behavior is that the
agent uses the package, covers required sources, names gaps, respects
federation boundaries, and avoids calendar-only or prompt-only reasoning when
state surfaces exist.

## Implementation Sequence

### Phase 0: Eval Gate

Run the pending FLIP/evaluator tasks for the recently completed contracts,
freshness backlog, personal state, SampleCo, PortfolioCo, and ResearchCo. Convert findings into
follow-up tasks before changing contracts again.

### Phase 1: Federation Packs

Define and validate `InstanceFederationPack` so personal state, SampleCo, PortfolioCo,
ResearchCo, and Relationship Substrate can describe governed cross-instance query
routes without raw materialization.

### Phase 2: Connector Module Kit

Document and test the lifecycle for adding modules. Use Spotify, Garmin, and
Relationship Substrate as examples because they cover historical caches, local
syncs, live API gaps, correction writes, and no-materialization federation.

### Phase 3: Instance Readiness Promotion

Move PortfolioCo and ResearchCo from scaffolded roots to package-ready first
instances with declared source gaps, preflight/freshness evidence, and rendered
agent packages.

### Phase 4: Freshness Repair Loops

Repair the highest-value live gaps: Spotify live OAuth, SampleCo Linear/GitHub, and
SampleCo transcript pipelines. Each repair must update readiness records and package
output rather than only changing private connector behavior.

### Phase 5: Pressure Harness

Add real-question package pressure tests for Sam, Iris, Helena, and Scout.
These tests should assert source coverage, gap naming, route/tool visibility,
and materialization boundaries rather than brittle answer text.

## Done Criteria

This model is complete enough for the next release when:

- `InstanceFederationPack` schema, examples, docs, and tests exist.
- Existing personal state and SampleCo federation routes are represented as federation
  packs.
- PortfolioCo and ResearchCo have first packages that render from their repo roots.
- Connector module kit docs explain how to add Spotify-like, Garmin-like, and
  Relationship-Substrate-like modules without core schema edits.
- Real-question pressure tests pass for Sam and Iris and have scaffolded
  cases for Helena/Scout.
- All generic validation and focused tests pass.
- Open-source examples contain no private corpora, names, account data, tokens,
  listening history, health records, or private relationship records.

## Non-Goals

- Do not build a hosted control plane.
- Do not require every connector to be live before packages are useful.
- Do not move source-owned records into State System when a federated query
  route is the right boundary.
- Do not encode source behavior as private prompt instructions when a contract,
  package field, or rendered CLI output can carry it.
