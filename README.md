# State System

State System is a generic model-mediated substrate for tracking organizational
state.

It helps humans and agents maintain durable, scoped records of:

- what appears to be true now;
- why that view changed;
- which evidence supports it;
- what remains uncertain or stale;
- what needs attention;
- which actions have been proposed, approved, blocked, or taken.

The model interprets meaning and proposes state transitions. Code owns schemas,
evidence references, access policy, freshness checks, persistence, audit, and
execution boundaries.

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

## Product Boundary

This repository is the product surface. It owns:

- schemas and examples;
- the file-backed CLI runtime;
- source-module, tool-action, question-route, and federation-pack contracts;
- instance preflight and source freshness records;
- agent package rendering and pressure tests;
- public docs and tests.

A deployed state root owns private runtime material:

- live state records;
- credentials and local paths;
- source-owned indexes;
- generated package exports;
- preflight and freshness evidence from live adapters;
- operational artifacts.

Do not commit private corpora, credentials, mutable source indexes, generated
private package exports, or local runtime artifacts to this repo.

## Agent Integration

Agents should start with [AGENTS.md](AGENTS.md) and
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

## Integrating Sources

Every source integration follows the same path:

1. Add or update a source module in
   `examples/source-modules/source-module-core-connectors.json`.
2. Declare the connector in an instance capability pack or deployed runtime
   capability record.
3. Record preflight evidence to prove or fail live access.
4. Record freshness evidence with checked time, source watermark, stale-after,
   lag where available, and explicit status.
5. Declare source-owned index refs when retrieval exists.
6. Add adapter commands to a fleet freshness manifest when refresh can be run
   mechanically.
7. Rebuild/export the instance agent package.
8. Add or update package pressure questions for affected answer paths.

Detailed docs:

- [docs/source-modules.md](docs/source-modules.md)
- [docs/runbooks/open-source-onboarding.md](docs/runbooks/open-source-onboarding.md)
- [docs/runbooks/fleet-freshness-runner.md](docs/runbooks/fleet-freshness-runner.md)

## Runnable Surfaces

Validate all examples:

```bash
python3 -m state_system.cli --project-root . validate
```

Run the report suite:

```bash
python3 -m state_system.cli --project-root . report-suite-run --output-dir /tmp/state-system-report-suite
```

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
