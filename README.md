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
- `docs/app-substrate-contract.md` - app-facing contract for shared state, proposals, evidence, and approval flows across the new application repos
- `docs/specs/2026-04-28-state-system-design.md` - initial system design
- `docs/specs/2026-04-28-state-system-speedrift-plan.md` - Speedrift execution anchor for the first deployment
- `docs/concepts/` - focused concept notes
- `docs/concepts/end-state-architecture.md` - target architecture and reusable PAIA assets
- `docs/concepts/agent-memory.md` - individual agent memory and promotion to shared state
- `docs/concepts/paia-memory-adapter-boundary.md` - adapter boundary for reusing PAIA memory without making State System PAIA-only
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
- `schemas/` - draft JSON schemas for source events, state objects, journals, triggers, model review packets, model outputs, commit results, review signals, memory entries, governance policies, personas, facets, recent-change entries, and context packages
- `examples/` - example state packets and end-to-end traces for Laura and Patrick, including GitHub commitment fixtures

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

## Validation

Run the local contract and fixture harness:

```bash
python3 -m unittest tests/test_contracts.py tests/test_stores.py tests/test_source_events.py tests/test_runner_reviewer.py tests/test_committer_materializer.py tests/test_governance_pressure.py tests/test_recent_context_packaging.py tests/test_cli.py tests/test_e2e_pressure_harness.py tests/test_cli_runtime.py tests/test_git_source_adapter.py tests/test_live_git_runtime.py
```

## Runtime V0 CLI

The first local runtime loop is exposed as JSON CLI commands:

```bash
python3 -m state_system.cli --project-root . validate
python3 -m state_system.cli --state-root /path/to/runtime seed-runtime --repo-ref repo.state-system --created-at 2026-05-01T18:45:00Z
python3 -m state_system.cli --state-root /path/to/runtime trigger examples/source-linear-southern-abrasives-won.json
python3 -m state_system.cli --state-root /path/to/runtime git-commit-event /path/to/commit.json --repo-ref repo.state-system --observed-at 2026-05-01T18:01:00Z --candidate-state-ref state.repo.state-system.runtime --ingest
python3 -m state_system.cli --state-root /path/to/runtime git-commit-from-repo . --commit HEAD --repo-ref repo.state-system --observed-at 2026-05-01T18:46:00Z --candidate-state-ref state.repo.state-system.runtime --ingest
python3 -m state_system.cli --state-root /path/to/runtime index-source-recent source.git.repo.state-system.<sha> --created-at 2026-05-01T18:47:00Z --summary "Latest commit changed runtime support." --routes /path/to/routes.json --watermark-ref git:repo.state-system:commit:<sha> --stale-after 2026-05-02T18:47:00Z
python3 -m state_system.cli --state-root /path/to/runtime review source.linear.southern-abrasives-won --packet-id review_packet.linear.southern-abrasives-won --created-at 2026-04-28T16:05:30Z --persona examples/patrick-persona.json --resolved-evidence /path/to/evidence.json --governance-constraints /path/to/governance.json
python3 -m state_system.cli --state-root /path/to/runtime commit examples/linear-southern-abrasives-won-model-proposal-output.json --created-at 2026-04-28T16:07:00Z --evidence-ref linear:deal:southern-abrasives
```
