# Open-Source Ecosystem State System Speedrift Plan

Date: 2026-05-18

## Objective

Move State System from working private deployments toward an open-source,
CLI-ready, agent-facing package layer that works across Braydon's live
ecosystem: b-state, LFW, Navicyte, Synthyra, and reusable Relationship
Substrate.

The target is not a demo. A fresh Codex or Claude session should be able to
start in a deployed repo, read repo-local guidance, load the package/read model,
understand source readiness and gaps, and use declared routes/tools without
private prompting.

## Current Ground Truth

State System now has generic contracts for:

- source modules
- tool actions
- question routes
- instance capability packs
- instance understanding surfaces
- instance agent packages

b-state and LFW have proven the contract shape:

- b-state exposes Sam's package with Spotify, Garmin Connect, Relationship
  Substrate, subject notes, workboard, msgvault, agentmem, local path, and LFW
  federation.
- LFW exposes Caroline's package with company state first and a governed
  federated relationship route into Braydon personal relationship evidence.
- Relationship Substrate owns people, organizations, affiliations,
  interactions, and subject notes. State System declares/federates the module;
  it must not become a second relationship data store.

## North Star

State System succeeds when:

- another agent can add a connector without editing core pack schemas;
- another agent can scaffold a new company/person/project state instance;
- packages expose source readiness, freshness, gaps, routes, tools, governance,
  and no-materialization boundaries in typed fields;
- Sam, Caroline, and future agents can answer real questions from package JSON
  and rendered CLI output;
- private source data stays in deployed instances;
- open-source examples remain synthetic and safe;
- drift tests catch contract, source, route, and freshness regressions.

## Workstreams

### 1. Core Contract Hardening

Owner: `state:1.1`

Deliver:

- conformance tests that every package connector has a source module;
- every route tool has a tool action contract or declared module read surface;
- every route has structured source coverage, fallback, gap, and answer policy;
- renderer output is good enough for fresh sessions;
- docs for adding modules, tools, routes, and state instances.

### 2. Relationship Substrate OSS Readiness

Owner: `per:3.1`, coordinated by `state:1.1`

Deliver:

- public schemas/typed models for `person`, `organization`, `affiliation`,
  `interaction`, and `subject_note`;
- primary CLI docs for `record-subject-note` and `list-subject-notes`;
- compatibility notes for person-note aliases;
- synthetic fixtures with no private names/emails/paths;
- tests proving subject notes demote/explain, not hide;
- clear boundary: source-owned correction writes are not external side effects.

### 3. b-state Daily-Use Readiness

Owner: `state:3.1`

Deliver:

- Sam package and instance-understanding stay aligned to current contracts;
- Spotify historical cache remains usable with typed stale/live OAuth gap;
- Garmin Connect remains ready/fresh with typed local-sync status;
- relationship routes answer real questions from Relationship Substrate,
  msgvault, agentmem, workboard, and LFW federation;
- `/Users/braydon/projects/personal/b-state` gets repo-local agent guidance if
  missing or stale.

### 4. LFW Daily-Use Readiness

Owner: `state:2.1`

Deliver:

- Caroline package/read model stays contract-aligned;
- root `AGENTS.md` and `CLAUDE.md` explain LFW state usage and the governed
  relationship route;
- Linear/GitHub/transcript gaps stay visible and typed;
- package answers preserve LFW-first, no-personal-materialization behavior.

### 5. Navicyte Instance Scaffold

Owner: `state:4.1`

Deliver:

- company state root scaffold;
- source module declarations;
- preflight/freshness/readiness gap records;
- first agent package;
- repo-local agent guidance;
- validation commands and runbook.

### 6. Synthyra Instance Scaffold

Owner: `state:5.1`

Deliver:

- company state root scaffold;
- source module declarations;
- preflight/freshness/readiness gap records;
- first agent package;
- repo-local agent guidance;
- validation commands and runbook.

## Done Criteria

The current execution wave is done when:

- State System validation and tests pass;
- b-state and LFW deployed validations pass;
- Navicyte and Synthyra have minimally usable state roots and first packages;
- Relationship Substrate has OSS-readiness contracts/docs/fixtures planned or
  implemented with tests;
- fresh Codex/Claude sessions in LFW and b-state know how to use their state
  systems from repo-local guidance;
- Workgraph has follow-up tasks for unresolved connector freshness and OSS
  packaging gaps.

## Drift Controls

- Run `./.workgraph/drifts check --task <task_id> --write-log --create-followups`
  at task start and before completion.
- Treat yellow drift as advisory unless it finds concrete contract drift.
- Convert new uncertainty into explicit Workgraph follow-ups.
- Do not copy private corpora into open-source examples.
- Preserve deployed instance privacy boundaries and no-materialization routes.
