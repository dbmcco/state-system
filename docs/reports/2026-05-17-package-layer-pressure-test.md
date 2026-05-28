# Package Layer Pressure Test

Date: 2026-05-17

## Objective

Prove the CLI-ready agent-facing package layer can build, render, and validate
packages from the deployed b-state and LFW runtime roots without requiring all
connectors to be ready and without executing protected actions.

## Commands

```bash
python3 -m unittest tests/test_instance_agent_package_e2e.py
python3 -m unittest discover -s tests
python3 -m state_system.cli --project-root . validate
python3 -m state_system.cli --project-root . --state-root /path/to/personal-state instance-agent-package-render instance_agent_package.e2e.acme_ops.samantha
python3 -m state_system.cli --project-root . --state-root /path/to/state-system-runtime instance-agent-package-render instance_agent_package.e2e.lfw.caroline
```

## Generated Runtime Packages

b-state:

- `/path/to/personal-state/state/instance-agent-packages/instance_agent_package.e2e.acme_ops.samantha.json`

LFW:

- `/path/to/state-system-runtime/state/instance-agent-packages/instance_agent_package.e2e.lfw.caroline.json`

## Assertions

b-state package:

- Builds from `/path/to/personal-state`.
- Renders as a `State System Instance Agent Package`.
- Includes Garmin Connect and Spotify as planned/unknown source gaps.
- Includes LFW as an available federated instance metadata surface while keeping
  b-state access/freshness/index status planned or unknown.
- Does not authorize protected execution.

LFW package:

- Builds from `/path/to/state-system-runtime`.
- Renders as a `State System Instance Agent Package`.
- Includes `connector.lfw.msgvault` with `freshness=failed`.
- Excludes personal Garmin Connect and Spotify sources.
- Does not authorize protected execution.

## Result

- E2E pressure test passed.
- Full unit suite passed: 165 tests.
- Example schema validation passed: 124 examples.
- Runtime package schema validation passed for b-state and LFW packages.
- `specdrift` for the e2e task was green.

## Remaining Gaps

These are explicit source readiness gaps, not package-layer blockers:

- b-state msgvault and agentmem access remain planned.
- b-state workboard freshness remains unknown.
- b-state Garmin Connect and Spotify remain planned/unknown.
- b-state LFW federation metadata is available, but b-state access/freshness/index
  status for that source remains planned/unknown.
- LFW msgvault freshness remains failed.
