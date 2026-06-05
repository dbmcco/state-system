# Fleet Freshness Runner Design

Date: 2026-05-19

## Goal

Keep multiple state instances package-ready through one manifest-driven refresh
loop. The first fleet is personal state, SampleCo, PortfolioCo, and ResearchCo, but the contract
must be generic enough for future company or personal state roots.

## Design

`FleetRefreshManifest` declares a fleet of instance state roots. Each instance
entry names:

- `state_root`
- `instance_ref`
- `agent_ref` / `persona_ref`
- `package_id`
- output directories for generated read models
- optional adapter commands

The runner executes explicit adapter commands first, then regenerates:

1. instance preflight read model
2. instance source freshness read model
3. instance understanding surface
4. instance agent package
5. instance package read model

It can optionally run package pressure against the refreshed package set.

## Source Boundary

The runner does not make source-specific freshness claims for delegated systems
by itself. Knowledge Store, Drive, msgvault, Linear, GitHub, Garmin, Spotify, relationship
substrate, and similar systems must either:

- already have recorded preflight/freshness evidence in the state root, or
- expose an adapter command in the fleet manifest that records that evidence.

If an adapter is absent or fails, the refreshed package must keep the source gap
visible.

## CLI

```bash
python3 -m state_system.cli \
  --project-root /path/to/state-system \
  fleet-refresh-run /path/to/fleet-refresh.json \
  --checked-at 2026-05-19T20:00:00Z \
  --stale-after 2026-05-19T21:00:00Z \
  --output-dir /tmp/fleet-refresh
```

Use `--dry-run` to validate the manifest and planned adapter commands without
executing adapters or writing packages.

## Done

The feature is complete when:

- manifest schema validates examples
- CLI emits a JSON report with per-instance package paths, source status counts,
  source gaps, adapter command results, and pressure results
- downstream state roots have manifests that can be run from their repo context
- four-package pressure passes after refresh
