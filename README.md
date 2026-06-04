# State System

![State System hero](docs/assets/state-system-hero.png)

State System is a generic state substrate for agents and humans operating across
many source systems.

It solves a practical agent reliability problem: an agent is often asked, "what
is the current state?" while the relevant evidence is scattered across docs,
messages, tasks, CRM records, calendars, repositories, memory systems, and local
runtime artifacts. Some sources are fresh, some are stale, some are unreachable,
some are only declared, and some are governed by another instance. Without an
explicit state layer, agents either over-trust whatever context they saw last or
hide uncertainty in prose.

State System makes that boundary explicit. It records what appears to be true,
why that view changed, which evidence supports it, which sources are fresh or
stale, what remains uncertain, which routes/tools are allowed, and which actions
require governance before execution.

## Core Idea

State is not a note, a prompt, or a transient model context dump.

State is a durable, scoped record of:

- what appears to be true now;
- why that view changed;
- which evidence supports it;
- which source systems are reachable and fresh;
- what is stale, failed, unknown, planned, or federated;
- what needs attention;
- which actions have been proposed, approved, blocked, or taken.

The model interprets meaning and proposes state transitions. Code owns schemas,
evidence references, source access status, freshness checks, persistence, audit,
governance boundaries, and execution safety.

## What This Repo Provides

This repository is the product surface. It includes:

- JSON schemas for state records, source modules, freshness, packages, routes,
  tool actions, federation packs, and agent-facing artifacts;
- a file-backed Python CLI runtime;
- source integration contracts for declaring connector behavior;
- preflight and freshness recorders;
- instance understanding surfaces and agent package rendering;
- package pressure tests that check whether a package exposes enough structure
  for an agent to answer responsibly;
- public fixtures using neutral example instances.

A deployed state root owns private runtime material: live state records,
credentials, local paths, source-owned indexes, generated package exports,
adapter evidence, and operational artifacts. Those do not belong in this repo.

## How It Works

1. **Declare sources.** A source module says what a connector type means:
   source refs, access mode, preflight contract, freshness contract, index
   ownership, tools, read/write surfaces, gap behavior, and governance defaults.
2. **Declare instance capability.** A deployed instance names the connectors,
   indexes, tools, and governance surfaces it intends to use.
3. **Prove access with preflight.** Preflight records whether a connector is
   reachable. `passed` proves live access; `failed` and `planned` remain visible
   gaps.
4. **Prove recency with freshness.** Freshness records checked time, source
   watermark, stale-after, lag where available, and status:
   `fresh`, `stale`, `failed`, `unknown`, or `planned`.
5. **Render understanding.** The runtime joins capability, preflight,
   freshness, indexes, and gaps into an inspectable read model.
6. **Render agent packages.** Packages expose routes, source readiness, tool
   action refs, freshness gaps, evidence refs, federation packs, and governance
   boundaries.
7. **Pressure test packages.** Operational questions assert that packages expose
   the routes, sources, gaps, freshness, tools, and federation boundaries an
   agent needs before answering.

## Integrating Sources

Source integrations are first-class. To add one:

1. Add a module to
   `examples/source-modules/source-module-core-connectors.json`.
2. Give it a stable `connector_type`, safe `source_ref` examples, supported
   instance kinds, module modes, preflight contract, freshness contract, index
   contract, tool contract, gap behavior, and governance defaults.
3. Add matching connector declarations to an instance capability pack or a
   deployed runtime capability record.
4. Record preflight evidence:

   ```bash
   python3 -m state_system.cli --project-root . \
     --state-root /path/to/state-root \
     instance-preflight-record \
     --preflight-ref preflight.state_instance.sampleco.connector.sampleco.folio \
     --instance-ref state_instance.sampleco \
     --connector-ref connector.sampleco.folio \
     --source-ref folio:tenant:sampleco \
     --connector-type folio \
     --status passed \
     --checked-at 2026-05-18T12:05:00Z \
     --stale-after 2026-05-18T13:05:00Z \
     --evidence-ref local-path:/srv/folio/sampleco
   ```

5. Record freshness evidence:

   ```bash
   python3 -m state_system.cli --project-root . \
     --state-root /path/to/state-root \
     instance-source-freshness-record \
     --instance-ref state_instance.sampleco \
     --connector-ref connector.sampleco.folio \
     --source-ref folio:tenant:sampleco \
     --connector-type folio \
     --status fresh \
     --checked-at 2026-05-18T12:05:00Z \
     --source-watermark folio.indexed_at:2026-05-18T12:04:00Z \
     --stale-after 2026-05-18T13:05:00Z \
     --evidence-ref freshness:folio:fresh:20260518T120500Z
   ```

6. Declare source-owned index refs when retrieval exists. State System may cite
   source indexes without owning raw corpora.
7. Add adapter commands to a fleet freshness manifest when the source can be
   refreshed mechanically.
8. Rebuild/export the instance agent package and add package pressure questions
   for answer paths affected by the source.

Detailed docs:

- [docs/source-modules.md](docs/source-modules.md)
- [docs/runbooks/open-source-onboarding.md](docs/runbooks/open-source-onboarding.md)
- [docs/runbooks/fleet-freshness-runner.md](docs/runbooks/fleet-freshness-runner.md)

## Agent Integration

Agents should consume rendered artifacts, not scrape private runtime roots.
Start with [AGENTS.md](AGENTS.md) and
[docs/agent-integration.md](docs/agent-integration.md).

The short contract:

- read rendered `InstanceAgentPackage` artifacts or
  `instance-agent-packages-read-model.json`;
- inspect source readiness, preflight, freshness, stale-after expiry, source
  gaps, route gaps, and federation gaps before answering;
- use explicit question routes, source module refs, tool action refs, and
  federation pack refs;
- do not infer source behavior from connector names;
- do not materialize raw federated data unless a pack explicitly permits it;
- treat captured agent output as evidence for review, not accepted truth;
- keep governance separate from freshness and preflight.

## Quickstart

From a clean checkout:

```bash
python3 -m unittest discover -s tests
python3 -m state_system.cli --project-root . validate
python3 -m state_system.cli --project-root . report-suite-run --output-dir /tmp/state-system-report-suite
```

Open `/tmp/state-system-report-suite/index.html` to inspect the generated
reports. The validation command checks shipped schemas and JSON examples; the
test suite checks runtime, package, freshness, federation, source-module, and
pressure-test contracts.

## Runnable Surfaces

Run a trace:

```bash
python3 -m state_system.cli --project-root . trace-run examples/traces/linear-deal-won.trace.json --output-dir /tmp/state-system-trace
```

Build a North Star answer substrate from packages:

```bash
python3 -m state_system.cli --project-root . north-star-answer \
  --query "What is the current state?" \
  --package sample=examples/instance-agent-package/instance-agent-package-sample-personal-samantha.json \
  --output-dir /tmp/state-system-north-star
```

Render the deterministic text view:

```bash
python3 -m state_system.cli --project-root . north-star-answer-render \
  /tmp/state-system-north-star/north-star-answer.json \
  --check \
  --output-path /tmp/state-system-north-star/north-star-answer.txt
```

## Public Fixtures

The shipped fixtures use neutral example organizations and instances such as
`SampleCo`, `ResearchCo`, `PortfolioCo`, and `sample_personal`. They are
contract fixtures, not required deployment names. Real deployments should use
their own instance refs, connector refs, source refs, package IDs, and freshness
manifests.

## Repository Map

- `state_system/` - Python runtime and CLI implementation.
- `schemas/` - JSON schemas for state, packages, freshness, routes, and tools.
- `examples/` - public schema-valid fixtures and trace manifests.
- `tests/` - unit, conformance, runtime, and pressure tests.
- `docs/NORTH_STAR.md` - intended direction and product boundary.
- `docs/system-diagram.html` - local architecture diagram.
- `docs/source-modules.md` - source connector extension contract.
- `docs/agent-integration.md` - runtime agent consumption contract.
- `docs/runbooks/` - public operator runbooks.

## Development Gates

Run these before publishing or merging:

```bash
python3 -m unittest discover -s tests
python3 -m state_system.cli --project-root . validate
python3 -m unittest tests.test_open_source_ecosystem_conformance -v
git diff --check
```
