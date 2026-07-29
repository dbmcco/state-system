# Fleet Freshness Runner

Use this when a set of state roots needs to be refreshed together before agents
answer operational questions.

## Command

```bash
python3 -m state_system.cli \
  --project-root /path/to/state-system \
  fleet-refresh-run /path/to/fleet-refresh.json \
  --output-dir /tmp/state-system-fleet-refresh
```

For deterministic runs, pass explicit timestamps:

```bash
python3 -m state_system.cli \
  --project-root /path/to/state-system \
  fleet-refresh-run /path/to/fleet-refresh.json \
  --checked-at 2026-05-19T20:00:00Z \
  --stale-after 2026-05-19T21:00:00Z \
  --output-dir /tmp/state-system-fleet-refresh
```

## What It Does

- Runs explicit adapter commands declared in the manifest.
- Exports instance preflight and source freshness read models.
- Regenerates the instance understanding surface.
- Rebuilds and exports the CLI-facing instance agent package.
- Generates a per-instance strategic-staleness read model from entity-current-state
  cards. When no live reviewer is wired, expired cards are surfaced as
  `awaiting_model_review` gaps; an empty projection is marked
  `no_reviewable_findings` rather than presented as a healthy review.
- Optionally runs package pressure over the refreshed package set.
- Writes a fleet report with package paths, source status counts, source gap
  refs, adapter command results, pressure results, and strategic-staleness paths
  plus each instance's strategic-staleness `review_status` and `status_reason`.

## Multi-root entity-current-state wiring

Fleet manifests may refresh entity-current-state projections from more than one
state root. Use the `entity_current_state.roots` array instead of the legacy
single `state_root` field:

```json
{
  "entity_current_state": {
    "roots": [
      {"state_root": "/path/to/b-state", "label": "b_state"},
      {"state_root": "/path/to/company", "label": "company"}
    ],
    "output_dir": "entity-current-state"
  }
}
```

Each root is refreshed independently. A missing or unreachable root is reported
as a `gap.fleet_ecs.<label>.state_root_missing` gap and fails the overall fleet
report, so a missing satellite cannot make the rest of the fleet look fresh.
The legacy single-root shape (`{"state_root": "..."}`) is still accepted.

## Navicyte refresh path

`examples/fleet-refresh/fleet-refresh-navicyte.json` is the product-supported
refresh manifest for the Navicyte state instance. It declares Notion and email
source connectors through delegated adapter commands, surfaces their freshness
state in the generated package, and does not copy any private Navicyte corpus or
credentials into the repository. Navicyte is covered by default; if an operator
decides to drop the satellite, that decision must be recorded in a non-code
artifact before removing the manifest.

By default each instance refresh materializes
`<state_root>/strategic-staleness/strategic-staleness-read-model.json`. The
read model carries one entry per `entity_id`:

- If a reviewer is wired, the model's judgment is carried verbatim
  (`classification`, `recommended_action`, `confidence`, `reviewed_at`,
  `review_packet_id`).
- If no reviewer is wired, expired ECS cards are emitted with
  `review_status: awaiting_model_review`, `validity_window_exceeded: true`,
  the declared `stale_after`, and evidence refs. If there are no reviewable ECS
  findings, the top-level read model is marked
  `review_status: no_reviewable_findings`. Both cases are explicit status
  outputs, not claims that the content is healthy.

To replay recorded model judgments during a refresh:

```bash
python3 -m state_system.cli \
  --project-root /path/to/state-system \
  fleet-refresh-run /path/to/fleet-refresh.json \
  --reviewer recorded \
  --output-dir /tmp/state-system-fleet-refresh
```

To wire a live reviewer, supply an injected model client programmatically; the
CLI `--reviewer live` flag is rejected before any per-instance writes because
the CLI cannot supply a model client. Without a client the unsupported
configuration returns an error so callers cannot accidentally fabricate judgment.

The standalone scheduled runners are also deterministic inputs:

```bash
python3 -m state_system.cli --project-root /path/to/state-system \
  staleness-review-run --reviewer recorded \
  --freshness-dir /path/to/freshness --as-of 2026-06-25T12:00:00Z \
  --output-dir /tmp/staleness-review

python3 -m state_system.cli --project-root /path/to/state-system \
  strategic-review-run --reviewer recorded \
  --entity-current-state-dir /path/to/entity-current-state \
  --as-of 2026-06-25T12:00:00Z \
  --output-dir /tmp/strategic-staleness
```

## What It Does Not Do

- It does not infer live source access.
- It does not call credentialed systems unless a manifest adapter command does.
- It does not copy raw source corpora into state roots or generic examples.
- It does not make stale sources fresh by regenerating packages.

## Interpreting Results

- `ok=true`: required adapters passed and package pressure passed if configured.
- `status=refreshed`: read models/package were regenerated.
- `status=failed`: at least one required adapter failed.
- `source_status_counts`: grouped as `access|freshness|understanding`.
- `source_gap_refs`: the gaps agents must caveat before answering.

## Durable Scheduler Safety

The macOS wrapper at `scripts/run-fleet-refresh.sh` gives each instance a
stale-safe lock and uses one shared lock across instances. The shared lock is
intentional: several deployed adapters query MsgVault, whose daemon should not
be hit concurrently by the fleet. A timed-out adapter is terminated together
with its descendant process tree, and the wrapper removes both locks on exit.
A stale or unavailable source remains failed or unknown in the report; the
scheduler does not convert that gap into freshness.

## Downstream Pattern

Each downstream state root should carry a manifest at:

```text
fleet-refresh/instance-refresh.json
```

The ecosystem-level manifest can reference those same state roots or run a
single package-pressure check across all regenerated packages.
