# Runtime V0

Runtime v0 turns the design harness into one practical local operating loop.

It is not the final service architecture. It is the smallest runtime shape that
lets Codex, Claude Code, opencode, and future agent runtimes ask State System
for bounded state context instead of reading the whole repo or reconstructing
state from raw files.

## Goal

Runtime v0 should run this loop against file-backed state:

```text
source event
  -> trigger
  -> review packet
  -> model or fixture output
  -> commit result
  -> journals, memory, review signals, snapshots
  -> recent change
  -> persona package
```

The loop proves the layer boundaries work before adding a database, daemon,
MCP server, or live model provider.

## Access Surface

The first access surface is CLI JSON.

Agents should call explicit commands:

- `trigger` to ingest source events
- `review` to build a review packet from a trigger
- `commit` to apply a model or fixture output
- `index-recent` to create a recent-change entry from source and commit refs
- `build-package` to assemble a persona recent-change package
- `recent`, `package`, `journal`, `memory`, `rollups`, and `get` to inspect state

This keeps agents from rummaging through implementation files or making private
guesses about what context they need.

## Storage

Runtime v0 stays file-backed.

The file store is acceptable at this stage because it is:

- deterministic for tests
- inspectable by humans
- easy to replay
- easy to replace with a database-backed adapter later

The runtime should use existing store abstractions, not hardcoded paths inside
business logic.

## Model Boundary

Runtime v0 does not call a live model provider.

The review command builds the packet a model would receive. The commit command
accepts an explicit model or fixture output. That keeps the runtime testable
while preserving the model-mediated contract:

- the model decides meaning
- the runtime validates and persists effects
- governance blocks unsafe or approval-required effects

## Agent Boundary

CLI and coding agents should consume packages, not global state.

Examples:

- Patrick asks for recent operational changes for a repo or deal.
- Laura asks for recent marketing-relevant changes.
- Codex asks for the package attached to the current task.
- Claude Code or opencode asks for the same package through the same contract.

The package is the working context. The underlying state registry remains the
auditable source.

## Deferred

Runtime v0 deliberately defers:

- database persistence
- API service
- MCP tools
- live model provider calls
- background sync workers
- agent runtime memory adapter implementation
- cross-repo federation
- autonomous source monitoring

Those should be added only after the local loop is boring and useful.
