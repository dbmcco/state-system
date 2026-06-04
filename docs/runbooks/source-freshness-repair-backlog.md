# Source Freshness Repair Backlog

Date: 2026-05-18

This backlog tracks source readiness gaps that remain after the open-source
package-layer contract pass. The State System should expose these gaps as typed
freshness, preflight, route, and package metadata; source owners repair the
underlying connector or pipeline.

## Current Principle

- Do not claim a source is fresh unless a source-owned preflight or freshness
  record proves it.
- Keep raw corpora in the source instance. Packages should carry refs,
  watermarks, gap ids, and safe summaries.
- A stale or missing source can still be visible to an agent package when the
  route contract explains the answer caveat and repair path.
- Connector-specific behavior belongs in `SourceModuleSpec`,
  `ToolActionContract`, and `QuestionRouteContract`, not in private prompts.

## Open Repair Items

| Gap | Owner | Current Package Behavior | Repair Path | Done When |
| --- | --- | --- | --- | --- |
| `gap.state_instance.sample_personal.connector.personal.spotify.freshness_stale` | personal state | Samantha can use historical Spotify cache with stale caveat. Module mode is `historical_cache`; live API is not fresh. | Restore matching Spotify OAuth client credentials or rerun OAuth, execute a real live sync, record typed credential status and source watermark, then rebuild Sam package. | `connector.personal.spotify` has access passed, freshness fresh, current `source_watermark`, and no stale gap in Sam package. |
| SampleCo Linear freshness | SampleCo | Repaired in the Caroline package from source-owned evidence. Current watermark: `linear.latest_updated_at:2026-05-15T19:38:27.710Z`; checked at `2026-05-18T18:31:59Z`. | Keep Linear freshness job running and regenerate Caroline when the watermark changes or expires. | Linear readiness has access passed, freshness fresh, checked_at/source_watermark/stale_after, and no Linear freshness gap in Caroline. |
| SampleCo GitHub freshness | SampleCo | Repaired in the Caroline package from source-owned evidence. Current watermark: `github.pushed_at:2026-05-15T19:35:42Z;repo:draftforge`; checked at `2026-05-18T18:32:00Z`. | Keep GitHub freshness job running and regenerate Caroline when the watermark changes or expires. | GitHub readiness has access passed, freshness fresh, checked_at/source_watermark/stale_after, and no GitHub freshness gap in Caroline. |
| SampleCo raw transcripts missing/planned | SampleCo | Transcript sources are declared as missing or planned and should not be used as proved meeting memory. | Add source-owned local path heartbeat for raw transcript location or mark the source intentionally unavailable with typed reason. | Raw transcript module has a proved access status or an explicit durable unavailable status with reason. |
| SampleCo processed transcripts missing/planned | SampleCo | Processed transcript understanding remains unavailable to Caroline. | Build the processed transcript pipeline, declare pipeline dependency from raw transcripts, emit index manifest and freshness watermark. | Processed transcript source has access passed, freshness fresh or bounded stale, index ready, and route/package refs include transcript evidence only when usable. |
| PortfolioCo scaffold connectors unproved | PortfolioCo | Helena scaffold declares modules but should treat them as not yet production-ready until preflight/freshness/index records exist. | Run source-owned preflight and freshness checks for declared modules, then generate package/read model with typed gap refs. | Every declared PortfolioCo module has explicit access, freshness, index status, checked_at, and gap refs where not ready. |
| ResearchCo scaffold connectors unproved | ResearchCo | Ingrid scaffold declares modules but should treat them as not yet production-ready until preflight/freshness/index records exist. | Run source-owned preflight and freshness checks for declared modules, then generate package/read model with typed gap refs. | Every declared ResearchCo module has explicit access, freshness, index status, checked_at, and gap refs where not ready. |
| Relationship Substrate evaluator infrastructure | Relationship Substrate / State System | Relationship Substrate implementation is validated, but FLIP/evaluator automation had infrastructure failures. | Repair evaluator backend or Claude CLI execution path separately from the substrate implementation. | FLIP and evaluator runs complete without manual override for relationship-substrate OSS tasks. |

## Required Contract Behavior

For each repair, package consumers should be able to read:

- `source_module_ref`
- `module_registry_ref`
- `module_mode`
- `access_status`
- `freshness_status`
- `index_status`
- `checked_at`
- `source_watermark`
- `stale_after`
- `preflight_contract_ref`
- `freshness_contract_ref`
- `gap_behavior_ref`
- `source_gap_refs`

Routes that depend on these sources should also expose:

- `route_contract_ref`
- `required_source_coverage`
- `required_tools`
- `optional_tools`
- `optional_external_context_tools`
- `tool_action_refs`
- `answer_contract_policy`
- `fallback_policy`
- `gap_behavior`

## Validation Loop

After each repair:

1. Regenerate the instance read model and agent package.
2. Render the package from the consuming repo root.
3. Verify source module, route contract, tool action, gap, and watermark fields
   are visible without private prompt knowledge.
4. Run generic State System validation:

```bash
python3 -m state_system.cli --project-root /path/to/state-system validate
python3 -m unittest discover -s tests
```

5. Run the instance-specific validator for the repaired repo.
