# Agent State Integrity and Refresh Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with Workgraph and run the repository validation gates before completion.

**Goal:** Restore typed State System package delivery to the affected agents, prevent frozen entity-state projections from masquerading as current, and schedule deterministic portfolio projection refresh without weakening fail-closed binding.

**Architecture:** Keep package identity external and fail-closed: deployment manifests provide `instance_ref`, `agent_ref`, and `persona_ref` to each agent process through `PAIA_STATE_*_REF` variables. Add entity-current-state projection as an optional fleet-level post-refresh artifact, separate from per-instance source-freshness refresh. Compute decay from the declared `stale_after` boundary at consumption time so stale persisted flags cannot hide expired state.

**Tech Stack:** Python 3, unittest/pytest, JSON schemas, launchd plists, Workgraph/Speedrift drift checks.

## Global Constraints

- Do not add loader fallbacks from package-internal identity; the typed loader remains fail-closed.
- Do not mutate source-owned truth; entity-current-state resolution remains mechanical and append-only.
- Do not add entity-current-state export inside `_refresh_instance`; it belongs to the fleet-level post-refresh path.
- Preserve unrelated dirty working-tree changes in all repositories.
- Every production behavior change gets a failing test first.
- Validate live plist changes with `plutil` and package-load canaries after reload.

---

### Task 1: Document and validate the deployment binding contract

**Files:**
- Modify: `docs/agent-integration.md`
- Modify live deployment artifacts: `~/Library/LaunchAgents/com.paia.{samantha,caroline,helena,ingrid}.plist`
- Test/verify: package JSON files referenced by those plists and `plutil`

**Interfaces:**
- Consumes: package bindings from each deployed `instance-agent-package` JSON.
- Produces: explicit runtime environment contract for `PAIA_STATE_INSTANCE_REF`, `PAIA_STATE_AGENT_REF`, and `PAIA_STATE_PERSONA_REF`.

- [ ] Add a deployment section to `docs/agent-integration.md` documenting the three variables, their source of truth, exact per-agent values, and the fail-closed consequence of omission.
- [ ] Add the three variables to the four live launchd plists without changing unrelated environment entries.
- [ ] Validate every plist with `plutil -lint` and confirm each value matches the package manifest.
- [ ] Reload each affected user launchd job only after file validation, then verify the process environment and package decision.

### Task 2: Add the fleet-level entity-current-state projection step

**Files:**
- Modify: `schemas/fleet-refresh-manifest.schema.json`
- Modify: `state_system/fleet_refresh.py`
- Modify: `tests/test_fleet_refresh.py`
- Modify: `docs/spec-ecs-consumption.md` or a focused state-system design note if the existing spec needs an explicit projection boundary.

**Interfaces:**
- Consumes: optional manifest field `entity_current_state` with `state_root` and optional `output_dir`.
- Produces: `entity-current-state/entity-current-state-read-model.json` and a report entry from a fleet-level post-refresh function.

- [ ] Write a failing test proving a configured fleet manifest regenerates the entity-current-state projection using the run `checked_at` as `as_of` and reports its path.
- [ ] Write a failing schema test for the optional `entity_current_state` manifest object.
- [ ] Implement a small fleet-level helper that builds the projection from `StateStoreBundle` after instance refreshes complete and writes the JSON atomically through the existing JSON-writing convention.
- [ ] Keep the step absent for manifests without `entity_current_state`; existing per-instance manifests retain their current behavior.
- [ ] Surface projection failure in the top-level fleet report and `ok` value rather than reporting a false green.
- [ ] Add the field to the b-state fleet manifest only after the code and tests pass.

### Task 3: Recompute entity-state decay at consumption time

**Files:**
- Modify: `/Users/braydon/projects/experiments/paia-agent-runtime/src/paia_agent_runtime/chief_of_staff/current_state.py`
- Modify: `/Users/braydon/projects/experiments/paia-agent-runtime/tests/test_chief_of_staff_current_state.py`

**Interfaces:**
- Consumes: renderer state containing `as_of` and card `stale_after` values.
- Produces: honest stale/decay wording even when persisted `is_stale` is false or missing.

- [ ] Add a failing test with a card whose `stale_after` precedes the packet `as_of` while `is_stale` is false; assert that the rendered packet exposes a stale warning and does not present the card as unqualified current state.
- [ ] Add a failing test for a card whose `stale_after` is after `as_of`; assert no false stale warning.
- [ ] Implement strict ISO timestamp comparison using the existing project time helpers or a small local parser with explicit invalid-timestamp behavior.
- [ ] Preserve model-owned card content and the existing effective/not-yet-effective behavior.
- [ ] Update the authoritative framing so it explicitly says expired cards have reduced precedence and require refresh before reliance.

### Task 4: Add package-load and projection canaries

**Files:**
- Modify or add focused tests in the owning repositories.
- Add a verification script only if an existing operational entry point cannot express the canary.

**Interfaces:**
- Consumes: live package paths, binding environment, refreshed b-state projection.
- Produces: repeatable evidence for `INCLUDED`, current `as_of`, and stale warning behavior.

- [ ] Run the runtime package-loader tests and the four live agent package checks after plist reload.
- [ ] Run a b-state fleet refresh and confirm the entity-state read model `generated_at` advances beyond June 16.
- [ ] Confirm raw record count and active entity IDs remain intact after regeneration.
- [ ] Record residual gaps for Ingrid’s CRM/tenant behavior and Helena’s conditional tools as separate follow-up work rather than mixing them into the State System fix.

### Task 5: Drift, review, and landing gates

**Files:**
- No unrelated source changes.

- [ ] Run the relevant Workgraph drift checks before and after each repository task.
- [ ] Run focused tests in `state-system` and `paia-agent-runtime`, then the existing repository quality gates.
- [ ] Review the diff for scope drift and confirm the loader binding gate is unchanged.
- [ ] Commit and push each repository change separately; report live plist changes separately because they are outside git.
