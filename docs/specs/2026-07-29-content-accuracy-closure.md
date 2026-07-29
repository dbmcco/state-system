# Content Accuracy Closure: Navicyte Coverage and ECS Manifest Wiring

**Status:** Decisions implemented — 2026-07-29.
**Scope:** State System product surface: fleet-refresh manifests, entity-current-state
projection, source-module contracts, and public fixtures.

## Decisions

### 1. Navicyte gets an explicit refresh path

No recorded operator decision says Navicyte should be dropped. Therefore the
default coverage decision is to give Navicyte its own product-supported refresh
manifest rather than leave it as an implicit gap.

- `examples/fleet-refresh/fleet-refresh-navicyte.json` is the canonical refresh
  manifest for `state_instance.navicyte`.
- `examples/instance-capability/instance-navicyte.json` declares the Notion and
  email source connectors and their retrieval surfaces.
- `examples/source-modules/source-module-core-connectors.json` now includes
  `source_module.notion` and `source_module.email` so the connector types have
  declared contracts.
- `examples/instances/state-instance-navicyte.json` provides the public,
  deployment-shaped state instance record.
- The manifest and fixtures use placeholder paths and public source refs only;
  no private Navicyte runtime corpus, credentials, or message bodies are
  committed.

If an operator later decides Navicyte should be decommissioned, that decision
must be recorded in a non-code decision artifact and reviewed before the manifest
is removed.

### 2. ECS manifest wiring supports b-state plus additional instance shapes

The fleet-refresh manifest now supports an `entity_current_state.roots` array
for multi-root projection. Each root has a `state_root` and a `label`. This
lets a single fleet refresh cover b-state (personal) and company/portfolio/other
shapes without collapsing them into one directory.

The legacy single-root `entity_current_state.state_root` shape remains valid for
backward compatibility.

### 3. Missing ECS wiring is reported as a gap

When a configured `entity_current_state` root does not exist on disk, the fleet
refresh marks that root `failed`, emits `gap.fleet_ecs.<label>.state_root_missing`,
and fails the overall fleet report. This prevents a missing satellite from
making the rest of the fleet look fresh.

## Acceptance mapping

| Acceptance criterion | Evidence |
|---|---|
| Navicyte has an explicit refresh manifest/path | `examples/fleet-refresh/fleet-refresh-navicyte.json`, `examples/instance-capability/instance-navicyte.json`, `source_module.notion`, `source_module.email` |
| ECS wiring supports b-state + one additional shape | `entity_current_state.roots` schema and `test_fleet_refresh_supports_b_state_plus_company_shape` |
| Missing ECS wiring reported as a gap | `test_missing_entity_current_state_root_is_reported_as_gap` |
| No private Navicyte corpus/credentials committed | All fixtures use placeholder paths and public refs |

## Rollback notes

- Revert `schemas/fleet-refresh-manifest.schema.json`,
  `state_system/fleet_refresh.py`, and the new Navicyte/ECS fixtures together.
- If b-state behavior regresses, preserve the legacy single-root path in
  `_refresh_entity_current_state`.
