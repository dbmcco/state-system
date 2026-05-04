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

## System Shape

![State System overview](docs/assets/state-system-overview.svg)

For a richer local orientation diagram, open `docs/system-diagram.html` in a
browser.

## Reviewer Path

If you are reviewing State System for the first time, read it in this order:

1. This README for the thesis, current runtime, and limits.
2. `docs/system-diagram.html` for the broader architecture map.
3. `docs/NORTH_STAR.md` for the intended direction.
4. `docs/concepts/first-deployment-implementation-blueprint.md` for the
   implemented runtime path.
5. One runnable trace in `examples/traces/`, starting with
   `examples/traces/linear-deal-won.trace.json`.
6. `docs/app-substrate-contract.md` and
   `docs/app-integration-pressure-tests.md` for the app-facing future state.

Good feedback targets:

- whether the source event, context package, model proposal, governance, and
  commit boundaries are the right boundaries
- where the model-mediated layer is too vague, too powerful, or not powerful
  enough
- what failure modes are missing around stale context, hidden heuristics,
  approval bypasses, and app-local state drift
- what would make this useful in another agent-heavy workflow

## What Works Today

The current repo is a working contract prototype, not only a reference design.
It can run a local JSON-backed runtime loop that:

- validates schemas and examples
- validates trace manifests
- ingests a source event with idempotency checks
- builds a model review packet from source evidence, state, persona, and
  governance context
- commits a fixture model proposal into journals, state snapshots, review
  signals, and rollup requests
- indexes recent changes for persona-specific routing
- builds and renders agent-readable context packages
- creates persisted agent activation records with goals, expected response
  types, allowed/prohibited actions, evidence refs, freshness, and capture
  policy
- renders activation records into agent-facing instructions plus the bounded
  context package
- captures raw agent responses with package and evidence refs
- writes a static user-test report at `index.html` for each trace run

The main functional surface is now a trace runner. A trace manifest declares the
source evidence, seed state, model proposal fixture, governance context, recent
change routing, context package, agent activation, rendered activation, and
captured response. The runner executes the flow and writes a machine-readable
report, a user-readable HTML report, and each intermediate artifact.

Canonical traces:

- `examples/traces/linear-deal-won.trace.json` proves accepted state update,
  materialized state, recent-change routing, context packaging, and agent
  response capture.
- `examples/traces/laura-approval-gated-publication.trace.json` proves
  governance can hold an external-facing action as pending approval without
  materializing state or executing the action.
- `examples/traces/laura-agent-activation.trace.json` proves an agent can be
  activated from a bounded context package, receive explicit action boundaries,
  and have its response captured without treating that response as truth.
- `examples/traces/laura-stale-context-refresh.trace.json` proves a stale
  package surfaces its validity window, refresh requirement, prohibited external
  action, and captured refusal to proceed externally before refresh.
- `examples/app-integrations/` now includes schema-valid contract fixture
  chains for Prospect Researcher -> Outreach Engine and Outreach reply -> CRM
  plus secondary contact and engagement-intelligence artifacts.

Run the one-command demo:

```bash
./scripts/demo_state_system.sh
```

The demo writes each generated artifact to a temporary directory and prints that
path at the end. It also prints the static report path:

```text
Report: /tmp/state-system-demo.XXXXXX/index.html
```

Run the current report suite:

```bash
python3 -m state_system.cli --project-root . report-suite-run --output-dir /tmp/state-system-report-suite
```

Open `/tmp/state-system-report-suite/index.html` to inspect the current
agent-activation trace report and app-integration contract report from one
place.

## What Is Designed Next

The app-facing substrate has its first schema-valid contract fixtures, but it
is not yet a runtime app service. The intended next functional slices are:

- Promote the Prospect Researcher -> Outreach Engine contract fixture into a
  runnable trace or app-substrate harness.
- Promote the Outreach reply -> CRM plus secondary contacts fixture into a
  runnable trace or app-substrate harness.
- Meeting Manager, Thoughtforge, and Visual Forge use the same source event,
  context package, proposal, approval, and commit pattern.
- Qualitative human judgment remains model-interpretable evidence, not hidden
  numeric scoring or hardcoded rules.

Before sharing externally, real-looking fixture names and source refs should be
anonymized.

## Initial Contents

- `docs/NORTH_STAR.md` - guiding North Star for the effort
- `docs/system-diagram.html` - standalone HTML/SVG orientation diagram with completeness key and workflow explainer
- `docs/app-substrate-contract.md` - app-facing contract for shared state, proposals, evidence, and approval flows across the new application repos
- `docs/app-integration-pressure-tests.md` - cross-app pressure tests for handoffs, approval gates, qualitative learning, and hidden heuristic drift
- `docs/specs/2026-04-28-state-system-design.md` - initial system design
- `docs/specs/2026-04-28-state-system-speedrift-plan.md` - Speedrift execution anchor for the first deployment
- `docs/concepts/` - focused concept notes
- `docs/concepts/end-state-architecture.md` - target architecture and reusable PAIA assets
- `docs/concepts/agent-memory.md` - individual agent memory and promotion to shared state
- `docs/concepts/paia-memory-adapter-boundary.md` - adapter boundary for reusing PAIA memory without making State System PAIA-only
- `docs/concepts/deep-reviewer-personas.md` - how antagonistic reviewer personas such as Miriam are used through Workgraph/Speedrift
- `docs/concepts/runtime-v0.md` - first practical local runtime loop from source event to persona package
- `docs/concepts/ontology.md` - first-cut organizational state ontology
- `docs/concepts/lfw-ontology-pressure-test.md` - concrete LFW example used to test the ontology
- `docs/concepts/state-update-lifecycle.md` - trigger-to-journal-to-snapshot lifecycle
- `docs/concepts/first-deployment-mode.md` - first deployment mode for the end-state architecture
- `docs/concepts/model-pressure-test.md` - scenario pressure test for the model-mediated decision layer
- `docs/concepts/model-reviewer-runtime-boundary.md` - production reviewer prompt, tool, and agent access boundary
- `docs/concepts/committer-and-governance.md` - how proposals become durable effects or pending/rejected signals
- `docs/concepts/governance-policy.md` - inspectable policy shape for approvals and blocked effects
- `docs/concepts/first-deployment-implementation-blueprint.md` - implementation path and fixture trace for the first deployment
- `docs/concepts/materialization-and-patch-semantics.md` - how accepted journal patches become snapshots
- `docs/concepts/patrick-ops-manager.md` - second persona and operational pressure test
- `docs/concepts/workgraph-speedrift-github-integration.md` - how State System attaches to execution, drift, and code collaboration systems
- `docs/concepts/model-mediation-drift-memory-loop.md` - how Speedrift model-agency findings become source events, review packets, memory, state, or Workgraph action proposals
- `docs/concepts/recent-change-registry-and-agent-opportunities.md` - recent-change indexing and persona-specific opportunity review
- `docs/concepts/agent-context-packages.md` - bounded persona-specific context packages for agents
- `docs/concepts/system-pressure-test.md` - system-level pressure test across routing, packaging, freshness, governance, and agent conflict
- `docs/concepts/routing-audit-and-freshness.md` - routing audit, excluded context, and package freshness rules
- `docs/concepts/catch-points.md` - where facts, meaning, routing, packages, opportunity, risk, and rollups are caught
- `docs/concepts/source-events-and-idempotency.md` - source event envelope, idempotency keys, sync context, and source watermarks
- `docs/concepts/backward-gap-audit.md` - thin backward pass before committer implementation
- `docs/concepts/speedrift-execution-lane.md` - Workgraph/Speedrift implementation lane and pressure-test gates
- `schemas/` - draft JSON schemas for source events, state objects, journals, triggers, model review packets, model outputs, commit results, review signals, memory entries, governance policies, personas, facets, recent-change entries, context packages, agent activations, and agent responses
- `examples/` - example state packets and end-to-end traces for Laura and Patrick, including GitHub commitment fixtures
- `examples/traces/` - runnable trace manifests for replaying source-event-to-agent-context flows
- `examples/app-integrations/` - app integration fixture trace anchors for Prospect Researcher, Outreach Engine, CRM, Meeting Manager, Thoughtforge, and Visual Forge

## First Personas

Laura is the first modeled persona: a marketing agent focused on positioning,
campaign momentum, audience fit, narrative clarity, and commercially grounded
creative judgment.

Laura is not a PAIA personal assistant. She is a work agent whose personality
is expressed through professional judgment facets. She is also a test case for
how persona-mediated interpretation can maintain broader organizational state,
such as marketing narrative and mission alignment.

Patrick is the second modeled persona: an operations manager agent focused on
source-of-truth discipline, stale-state detection, ownership clarity,
follow-through, and governance boundaries around contracts and commitments.

Patrick gives the system a comparison trace. Where Laura tests strategic and
market-facing interpretation, Patrick tests terse operational state: what is the
owner, what is the stage, what is missing, what is the next action, and what
requires human approval before external action.

Miriam is the first deep reviewer persona: an antagonistic critical reviewer and
systems epistemologist focused on source/evidence boundaries, category errors,
coherence failure, governance leaks, activation-to-use confusion, and downstream
effects that could make the system confidently wrong.

## Validation

Run the shareable functional demo:

```bash
./scripts/demo_state_system.sh
```

Run the canonical trace directly:

```bash
python3 -m state_system.cli --project-root . trace-run examples/traces/linear-deal-won.trace.json --output-dir /tmp/state-system-trace
python3 -m state_system.cli --project-root . trace-run examples/traces/laura-approval-gated-publication.trace.json --output-dir /tmp/state-system-approval-trace
python3 -m state_system.cli --project-root . trace-run examples/traces/laura-agent-activation.trace.json --output-dir /tmp/state-system-agent-activation
python3 -m state_system.cli --project-root . trace-run examples/traces/laura-stale-context-refresh.trace.json --output-dir /tmp/state-system-stale-refresh
```

Run the app-integration contract report:

```bash
python3 -m state_system.cli --project-root . app-integrations-run --output-dir /tmp/state-system-app-integrations
```

The app-integration report writes `app-integration-report.json` and
`index.html`. It currently checks the Prospect Researcher -> Outreach Engine
handoff and the Outreach reply -> CRM plus secondary contacts handoff.

Run the local contract and fixture harness:

```bash
python3 -m unittest tests/test_contracts.py tests/test_stores.py tests/test_source_events.py tests/test_runner_reviewer.py tests/test_committer_materializer.py tests/test_governance_pressure.py tests/test_recent_context_packaging.py tests/test_cli.py tests/test_e2e_pressure_harness.py tests/test_cli_runtime.py tests/test_git_source_adapter.py tests/test_live_git_runtime.py tests/test_agent_consumers.py tests/test_trace_runner.py tests/test_agent_activation.py tests/test_trace_reporting.py tests/test_app_integration_contracts.py tests/test_app_integration_runner.py
```

## Runtime V0 CLI

The first local runtime loop is exposed as JSON CLI commands:

```bash
python3 -m state_system.cli --project-root . validate
python3 -m state_system.cli --project-root . trace-run examples/traces/linear-deal-won.trace.json --output-dir /tmp/state-system-trace
python3 -m state_system.cli --project-root . trace-run examples/traces/laura-approval-gated-publication.trace.json --output-dir /tmp/state-system-approval-trace
python3 -m state_system.cli --project-root . trace-run examples/traces/laura-agent-activation.trace.json --output-dir /tmp/state-system-agent-activation
python3 -m state_system.cli --state-root /path/to/runtime seed-runtime --repo-ref repo.state-system --created-at 2026-05-01T18:45:00Z
python3 -m state_system.cli --state-root /path/to/runtime trigger examples/source-linear-southern-abrasives-won.json
python3 -m state_system.cli --state-root /path/to/runtime git-commit-event /path/to/commit.json --repo-ref repo.state-system --observed-at 2026-05-01T18:01:00Z --candidate-state-ref state.repo.state-system.runtime --ingest
python3 -m state_system.cli --state-root /path/to/runtime git-commit-from-repo . --commit HEAD --repo-ref repo.state-system --observed-at 2026-05-01T18:46:00Z --candidate-state-ref state.repo.state-system.runtime --ingest
python3 -m state_system.cli --state-root /path/to/runtime index-source-recent source.git.repo.state-system.<sha> --created-at 2026-05-01T18:47:00Z --summary "Latest commit changed runtime support." --routes /path/to/routes.json --watermark-ref git:repo.state-system:commit:<sha> --stale-after 2026-05-02T18:47:00Z
python3 -m state_system.cli --state-root /path/to/runtime review source.linear.southern-abrasives-won --packet-id review_packet.linear.southern-abrasives-won --created-at 2026-04-28T16:05:30Z --persona examples/patrick-persona.json --resolved-evidence /path/to/evidence.json --governance-constraints /path/to/governance.json
python3 -m state_system.cli --state-root /path/to/runtime commit examples/linear-southern-abrasives-won-model-proposal-output.json --created-at 2026-04-28T16:07:00Z --evidence-ref linear:deal:southern-abrasives
```

## Agent Activation Contract V0

Humans operate through agents in this design. A reporting surface may exist, but
the primary use path is: State System creates an activation record, an agent
acts from that bounded context, and the response is captured as evidence for the
next review loop.

Create and render an activation:

```bash
python3 -m state_system.cli --state-root /path/to/runtime activate-agent context.laura.southern-abrasives-won-opportunity --consumer consumer.codex --created-at 2026-05-03T10:00:00Z --activation-goal "Draft internal material and identify what requires approval." --expected-response-type proposal
python3 -m state_system.cli --state-root /path/to/runtime render-activation activation.context.laura.southern-abrasives-won-opportunity.consumer.codex.20260503T100000Z
```

Context packages can still be rendered directly for inspection or debugging:

```bash
python3 -m state_system.cli --state-root /path/to/runtime render-package context.laura.southern-abrasives-won-opportunity
```

Raw agent output is captured as a durable artifact linked back to the package
and evidence that shaped it:

```bash
python3 -m state_system.cli --state-root /path/to/runtime capture-response context.laura.southern-abrasives-won-opportunity /path/to/response.txt --consumer consumer.codex --created-at 2026-05-03T10:02:00Z --activation-id activation.context.laura.southern-abrasives-won-opportunity.consumer.codex.20260503T100000Z
```
