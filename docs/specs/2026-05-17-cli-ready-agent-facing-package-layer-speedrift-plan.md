# CLI-Ready Agent-Facing Package Layer Plan

Date: 2026-05-17

## Target

Build the agent-facing package layer for State System instances so a CLI can
produce a bounded, machine-readable and renderable package for an agent from:

- generic State System contracts and runtime commands
- deployed LFW company state at `/Users/braydon/projects/work/lfw/state-system`
- deployed personal b-state at `/Users/braydon/projects/personal/b-state`

The package must include current interpreted state surfaces, source readiness,
freshness, evidence/index refs, governance/action boundaries, and explicit gaps.
It must not hide unavailable sources or copy raw corpora from source systems.

## North Stars

- Generic State System defines schemas, validation, runtime builders, CLI
  commands, and examples.
- LFW is a deployed company instance. It must not inherit personal sources such
  as Garmin Connect or Spotify.
- b-state is a deployed personal instance. It may declare personal source-owned
  systems such as Garmin Connect and Spotify, but they remain planned until
  preflight and freshness prove otherwise.
- Relationship Substrate is a personal source-owned relationship index. b-state
  can expose read-only operating-picture and enrichment-backed contact-search
  action routes. LFW can consume that relationship index only through an
  explicit governed federated query route that forbids raw personal record
  materialization.

## Working Definition Of Done

This wave is working when:

- `state package-agent` or equivalent CLI commands can build and render an
  agent package for one LFW agent and one b-state agent.
- The JSON package validates against schema and includes source readiness,
  freshness, index refs, evidence refs, governance refs, and gap refs.
- Rendered output is suitable to hand to a CLI agent without extra hidden
  context.
- LFW and b-state runtime roots have generated package artifacts.
- Samantha's package exposes relationship follow-up and smaller-consulting-firm
  relationship routes. Caroline's package exposes the governed LFW federated
  relationship-index route for LFW-relevant contact questions.
- Cross-repo sync checks prove the generated artifacts agree with the generic
  contracts and each instance north star.

This wave is done when:

- generic tests and schema validation pass
- generated LFW and b-state runtime JSON validates
- specdrift is green for package-contract and package-cli tasks
- coredrift findings are either resolved or converted into explicit follow-ups
- a final cross-repo pressure test builds, renders, and validates both packages

## Execution Lanes

1. Generic contract lane: harden instance record IDs, finish federation, define
   the instance agent package schema, and add CLI build/render commands.
2. b-state lane: keep Garmin/Spotify planned but visible, generate Samantha
   package artifacts, and validate no raw corpora are copied.
3. LFW lane: improve deployed instance readiness/freshness, generate an LFW
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
