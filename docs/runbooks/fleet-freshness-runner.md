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
- Optionally runs package pressure over the refreshed package set.
- Writes a fleet report with package paths, source status counts, source gap
  refs, adapter command results, and pressure results.

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
