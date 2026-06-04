# Agent Integration

State System is a substrate that agents read from. It is not itself a chat
agent, memory product, skill, or tool registry. It gives agents typed state,
evidence, readiness, source routes, freshness, and governance boundaries so
they can answer without silently depending on stale or private context.

## What Agents Should Read

The primary agent-facing artifact is an `InstanceAgentPackage` rendered or
exported from a deployed state root:

```bash
python3 -m state_system.cli --project-root /path/to/state-system \
  --state-root /path/to/runtime-root \
  instance-agent-package-render <package_id>

python3 -m state_system.cli --project-root /path/to/state-system \
  --state-root /path/to/runtime-root \
  instance-agent-package-export \
  --output-dir /path/to/runtime-root/instance-agent-package
```

Agents should prefer the exported read model at:

```text
<state-root>/instance-agent-package/instance-agent-packages-read-model.json
```

The package is intentionally bounded. It contains interpreted state, source
readiness, freshness, route contracts, tool action refs, gap refs, governance
refs, and federation boundaries. It should not contain broad raw corpora.

## Freshness Before Answering

Agents must inspect freshness before using a package for operational answers:

- `freshness.status`
- `freshness.source_gap_refs`
- `freshness.expired_freshness_refs`
- source `stale_after`
- source `freshness_expired`
- source readiness status triples such as access, freshness, and understanding
- package-level answer policies that require refresh before external action

Freshness and preflight answer different questions:

- Preflight proves live access to a connector or records why access is not
  proved.
- Freshness proves source recency or records why recency is stale, failed,
  unknown, planned, or expired.
- Governance authorizes protected external action.

One does not imply the others.

## Routes And Tools

Agents should use the package's explicit route and tool contracts:

- `question_routes[]` says which kinds of questions can be answered and which
  source coverage is required.
- `tool_action_refs[]` points to allowed backing actions.
- `source_module_refs[]` identifies connector contracts.
- route gap refs tell the agent what to caveat or repair before answering.

Agents should not infer behavior from connector names such as `drive`,
`msgvault`, or `linear`. Connector behavior belongs in source modules and tool
action contracts.

## Federation

Federation packs declare governed cross-instance reads. They are the right
boundary for cases such as:

- a personal personal state instance reading SampleCo interpreted state;
- SampleCo querying a personal relationship substrate;
- portfolio rollups across company instances such as PortfolioCo and ResearchCo.

The default federation posture is summary/query access with no raw local
materialization. If `materialization_policy.local_materialization` is false, an
agent must not copy raw remote rows, messages, notes, transcripts, or private
records into the local instance.

## agent runtime Agents

For agent runtime, State System should be used through runtime packets and tools, not as
free-form prompt memory:

- agent runtime agent prompts can include a rendered company or instance scope packet.
- agent runtime tools can expose actions such as refresh, understanding, and search over
  State System read models.
- `AGENTS.md` / `CLAUDE.md` files should point agents to the relevant state
  root and package, but should not duplicate package contents.
- A skill can teach an agent how to use State System, but the source of truth is
  still the package/read-model contract plus source modules and governance.

This keeps State System as the substrate, agent runtime as a consumer/runtime, and source
systems as owners of their raw data and indexes.

## Write Boundary

Agents may propose updates, record evidence, or trigger refresh commands when a
runtime grants that capability. They should not directly mutate source-owned
truth or external systems unless the package exposes an allowed action and
governance permits it.

Captured agent responses are durable artifacts, not accepted state by default.
They become state only through the normal review, governance, and commit path.

