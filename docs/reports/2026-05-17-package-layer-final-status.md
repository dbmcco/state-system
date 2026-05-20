# Package Layer Final Status

Date: 2026-05-17

## Target

Close the first CLI-ready, agent-facing package layer for State System instances.
The target package layer lets an agent inspect declared source readiness,
freshness, evidence refs, governance constraints, action surfaces, and unresolved
gaps before using a deployed state instance.

## Current State

The package layer is implemented and testable for both deployed instances:

- Generic State System owns the package schema, examples, runtime builder, store
  collection, CLI commands, and agent rendering.
- b-state has a Samantha package generated under the personal runtime root.
- LFW has a Caroline package generated under the company runtime root.
- Garmin Connect and Spotify are included only in the b-state personal package
  as planned/unknown source surfaces. They are not treated as ready evidence.
- LFW federation appears in the b-state package as available federated metadata,
  while b-state access/freshness/index status for that federated source remains
  planned/unknown.

## Agent-Facing Commands

From `/Users/braydon/projects/experiments/state-system`:

```bash
python3 -m state_system.cli --project-root . --state-root /Users/braydon/projects/personal/b-state instance-agent-package-render instance_agent_package.braydon_personal.samantha
python3 -m state_system.cli --project-root . --state-root /Users/braydon/projects/work/lfw/state-system instance-agent-package-render instance_agent_package.lfw.caroline
```

Package build/list/export commands are also available:

```bash
python3 -m state_system.cli --project-root . --state-root /Users/braydon/projects/personal/b-state instance-agent-package-list
python3 -m state_system.cli --project-root . --state-root /Users/braydon/projects/work/lfw/state-system instance-agent-package-list
```

## Runtime Artifacts

b-state:

- `/Users/braydon/projects/personal/b-state/state/instance-agent-packages/instance_agent_package.braydon_personal.samantha.json`
- `/Users/braydon/projects/personal/b-state/state/instance-agent-packages/instance_agent_package.e2e.braydon_personal.samantha.json`
- `/Users/braydon/projects/personal/b-state/instance-agent-package/instance-agent-packages-read-model.json`

LFW:

- `/Users/braydon/projects/work/lfw/state-system/state/instance-agent-packages/instance_agent_package.lfw.caroline.json`
- `/Users/braydon/projects/work/lfw/state-system/state/instance-agent-packages/instance_agent_package.e2e.lfw.caroline.json`
- `/Users/braydon/projects/work/lfw/state-system/instance-agent-package/instance-agent-packages-read-model.json`

## Verification

Commands run:

```bash
python3 -m unittest discover -s tests
python3 -m state_system.cli --project-root . validate
jq empty /Users/braydon/projects/personal/b-state/instance-agent-package/instance-agent-packages-read-model.json /Users/braydon/projects/work/lfw/state-system/instance-agent-package/instance-agent-packages-read-model.json
python3 -m state_system.cli --project-root . --state-root /Users/braydon/projects/personal/b-state instance-agent-package-render instance_agent_package.braydon_personal.samantha
python3 -m state_system.cli --project-root . --state-root /Users/braydon/projects/work/lfw/state-system instance-agent-package-render instance_agent_package.lfw.caroline
```

Results:

- Unit tests: 166 passed.
- Example/schema validation: 124 examples passed.
- b-state and LFW runtime read models parse as JSON.
- Four generated runtime package JSON files validate against
  `schemas/instance-agent-package.schema.json`.
- `specdrift` is green for:
  - `state-agent-package-contract-v0`
  - `state-agent-package-cli-v0`
  - `state-agent-package-e2e-pressure-v0`

## Remaining Gaps

These are source readiness gaps, not package-layer blockers:

- b-state `msgvault` and `agentmem` access remain planned.
- b-state `workboard` freshness remains unknown.
- b-state Garmin Connect and Spotify access/freshness/index status remains
  planned or unknown.
- b-state LFW federation metadata is available, but b-state readiness status for
  that source remains planned/unknown.
- LFW `msgvault` access passes, but freshness is failed.

## Drift Status

`coredrift` remains yellow for the package-layer wave because the shared
worktree contains broad coordinated implementation churn and generated runtime
artifacts. The remaining scope/churn condition is represented as Workgraph task
`state-package-layer-dirty-tree-scope-audit-v0`.

That follow-up owns triage of the dirty tree, separation of intentional package
layer changes from older or parallel work, and the commit/ship plan for this
wave. No package-layer behavioral or schema validation failure is currently
blocking local testing.
