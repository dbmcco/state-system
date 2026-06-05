# CLI-Ready Agent-Facing Package Layer Plan

Date: 2026-05-17

## Target

Build the agent-facing package layer for State System instances so a CLI can
produce a bounded, machine-readable and renderable package for an agent from:

- generic State System contracts and runtime commands
- deployed SampleCo company state at `/path/to/state-system-runtime`
- deployed personal personal state at `/path/to/personal-state`

The package must include current interpreted state surfaces, source readiness,
freshness, evidence/index refs, governance/action boundaries, and explicit gaps.
It must not hide unavailable sources or copy raw corpora from source systems.

## North Stars

- Generic State System defines schemas, validation, runtime builders, CLI
  commands, and examples.
- SampleCo is a deployed company instance. It must not inherit personal sources such
  as Garmin Connect or Spotify.
- personal state is a deployed personal instance. It may declare personal source-owned
  systems such as Garmin Connect and Spotify, but they remain planned until
  preflight and freshness prove otherwise.
- Relationship Substrate is a personal source-owned relationship index. personal state
  can expose read-only operating-picture and enrichment-backed contact-search
  action routes. SampleCo can consume that relationship index only through an
  explicit governed federated query route that forbids raw personal record
  materialization.

## Working Definition Of Done

This wave is working when:

- `state package-agent` or equivalent CLI commands can build and render an
  agent package for one SampleCo agent and one personal state agent.
- The JSON package validates against schema and includes source readiness,
  freshness, index refs, evidence refs, governance refs, and gap refs.
- Rendered output is suitable to hand to a CLI agent without extra hidden
  context.
- SampleCo and personal state runtime roots have generated package artifacts.
- Nova's package exposes relationship follow-up and smaller-consulting-firm
  relationship routes. Iris's package exposes the governed SampleCo federated
  relationship-index route for SampleCo-relevant contact questions.
- Cross-repo sync checks prove the generated artifacts agree with the generic
  contracts and each instance north star.

This wave is done when:

- generic tests and schema validation pass
- generated SampleCo and personal state runtime JSON validates
- specdrift is green for package-contract and package-cli tasks
- coredrift findings are either resolved or converted into explicit follow-ups
- a final cross-repo pressure test builds, renders, and validates both packages

## Execution Lanes

1. Generic contract lane: harden instance record IDs, finish federation, define
   the instance agent package schema, and add CLI build/render commands.
2. personal state lane: keep Garmin/Spotify planned but visible, generate Nova
   package artifacts, and validate no raw corpora are copied.
3. SampleCo lane: improve deployed instance readiness/freshness, generate an SampleCo
   agent package, and validate personal sources stay excluded.
4. Sync and quality lane: compare generic examples with deployed runtime roots,
   run schema/tests/drift checks, and drive fix loops.

## Drift Rules

- Run `./.workgraph/drifts check --task <task> --write-log --create-followups`
  at task start and before task completion.
- Run `./.workgraph/specdrift wg check --task <task> --write-log
  --create-followups` on package contract, package CLI, and final pressure-test
  tasks.
- If a runtime source cannot be proven, record the gap; do not make deterministic
  code infer readiness.
- Convert connector/API uncertainty into follow-up tasks instead of burying it
  in package-generation code.
