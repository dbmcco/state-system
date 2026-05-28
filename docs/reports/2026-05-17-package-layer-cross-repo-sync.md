# Package Layer Cross-Repo Sync

Date: 2026-05-17

## Scope

This report compares the generic State System package-layer contracts with the
deployed b-state and LFW runtime artifacts.

## Generic Contracts

- Schema: `schemas/instance-agent-package.schema.json`
- Generic examples:
  - `examples/instance-agent-package/instance-agent-package-acme-ops-samantha.json`
  - `examples/instance-agent-package/instance-agent-package-lfw-caroline.json`
- CLI commands:
  - `instance-agent-package-build`
  - `instance-agent-package-list`
  - `instance-agent-package-export`
  - `instance-agent-package-render`

## Deployed Artifacts

b-state:

- Package JSON:
  `/path/to/personal-state/state/instance-agent-packages/instance_agent_package.acme_ops.samantha.json`
- Package read model:
  `/path/to/personal-state/instance-agent-package/instance-agent-packages-read-model.json`
- Instance understanding:
  `/path/to/personal-state/instance-understanding/instance-understanding-surface-read-model.json`

LFW:

- Package JSON:
  `/path/to/state-system-runtime/state/instance-agent-packages/instance_agent_package.lfw.caroline.json`
- Package read model:
  `/path/to/state-system-runtime/instance-agent-package/instance-agent-packages-read-model.json`
- Instance understanding:
  `/path/to/state-system-runtime/instance-understanding/instance-understanding-surface-read-model.json`

## North-Star Alignment

- Generic State System remains the product repo for schemas, runtime builders,
  examples, and CLI commands.
- b-state remains a deployed personal instance. Garmin Connect and Spotify are
  declared as personal source surfaces but are still planned/unknown, not usable
  evidence.
- LFW remains a deployed company instance. Garmin Connect, Spotify, and personal
  health/media sources are absent from the LFW package and source surfaces.

## Current Source Gaps

b-state package gaps:

- `connector.personal.msgvault`: access planned, freshness unknown.
- `connector.personal.agentmem`: access planned, freshness unknown.
- `connector.personal.workboard`: freshness unknown.
- `connector.personal.garmin_connect`: access planned, freshness unknown, index planned.
- `connector.personal.spotify`: access planned, freshness unknown, index planned.
- `connector.personal.lfw_state_system`: access planned, freshness unknown, index planned,
  while federated LFW metadata is available.

LFW package gaps:

- `connector.lfw.msgvault`: freshness failed.

## Validation

Commands run:

```bash
python3 -m unittest discover -s tests
python3 -m state_system.cli --project-root . validate
python3 -m state_system.cli --project-root . --state-root /path/to/personal-state instance-agent-package-render instance_agent_package.acme_ops.samantha
python3 -m state_system.cli --project-root . --state-root /path/to/state-system-runtime instance-agent-package-render instance_agent_package.lfw.caroline
```

Results:

- Unit tests: 165 passed.
- Example validation: 124 examples passed.
- b-state package schema validation: 0 errors.
- LFW package schema validation: 0 errors.
- Runtime package read models parse as JSON.

## Drift Notes

- `specdrift` was green for the package contract and package CLI tasks.
- `coredrift` is yellow because the shared worktree contains coordinated
  multi-task implementation and runtime artifact churn outside each small task's
  original touch set.
- No new blocking mismatch was found in this sync. Remaining gaps are source
  readiness gaps, not package-layer contract gaps.
