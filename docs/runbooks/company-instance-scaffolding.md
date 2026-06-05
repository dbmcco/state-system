# Company Instance Scaffolding

Use this runbook when creating a new company state instance such as SampleCo,
PortfolioCo, or ResearchCo.

The scaffold proves shape, not live access. A connector may be declared before
it is fresh or reachable, but gaps must be explicit.

## Files

A company instance should contain:

- `state/instance-capabilities/instance_capability_pack.<company>.json`
- `state/source-modules/source-module-registry-<company>.json` when the instance
  needs a local subset or overrides
- `instance-preflight/instance-preflight-<company>-*.json`
- `instance-source-freshness/instance-source-freshness-<company>-*.json`
- `state/instance-agent-packages/instance_agent_package.<company>.<agent>.json`
- a short runbook with refresh and validation commands

## Connector Rules

Every connector type used by the instance must exist in the generic source
module registry or in an instance-local module registry.

Common company connectors:

- `kb`
- `gws_drive`
- `msgvault`
- `local_path`
- `repo`
- `linear`
- `zulip`
- `docs`
- `state_system_instance`

Personal-only connectors such as `spotify` and `garmin_connect` should not be
added to company instances unless the company has a legitimate company-owned
source module with a different privacy boundary.

## Gap Rules

Do not treat declared sources as live evidence.

Record:

- access status
- freshness status
- latest watermark
- credential failure class, without secrets
- index status
- planned/missing pipeline dependencies

For transcript or generated-document pipelines, distinguish filesystem path
freshness from usable processed-document freshness.

## Agent Package Rules

Agent packages should expose:

- package `generated_at`
- source artifact timestamps or freshness refs
- required source coverage for each route
- fallback behavior when sources are stale or missing
- no-materialization boundaries for federated personal/company routes
- `federation_packs` for governed cross-instance routes, including remote
  instance refs, materialization policy, freshness/gap policy, and repair owner
- protected-action boundaries

The package can route questions before every connector is fully live, but it
must tell the agent which sources are missing, stale, or only declared.

## Federation Pack Rules

Use an `InstanceFederationPack` when a company package needs another instance or
source substrate. Do not copy remote raw data into the local instance.

Required package behavior:

- SampleCo relationship routes should expose the Relationship Substrate federation
  pack with `local_materialization=false`.
- Personal personal state routes that use SampleCo context should expose the SampleCo instance
  read pack and name SampleCo freshness/gap policy.
- PortfolioCo and ResearchCo scaffolds may expose portfolio federation as `planned`,
  but must keep readiness gaps visible until package renders prove access,
  freshness, and index status.
