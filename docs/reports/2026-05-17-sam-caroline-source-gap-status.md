# Sam and Caroline Source Gap Status

Date: 2026-05-17

## Objective

Make the deployed agent-facing packages usable for:

- Caroline over the LFW instance at `/path/to/state-system-runtime`
- Samantha over the personal b-state instance at `/path/to/personal-state`

## Changes Recorded

LFW / Caroline:

- Ran targeted `msgvault sync user@example.com`.
- Recorded fresh `connector.lfw.msgvault` source freshness with account last sync
  `2026-05-17T18:35Z`.
- Mirrored that freshness into the LFW company layer so the company
  understanding surface no longer carries the old msgvault freshness failure.
- Regenerated LFW preflight, freshness, understanding, and agent package read
  models.

b-state / Samantha:

- Ran targeted `msgvault sync user@example.com`.
- Proved personal `msgvault` access and freshness.
- Proved `agentmem` access and freshness through `am admin stats --tenant example`
  and `am retrieve context --tenant example`.
- Marked workboard freshness fresh from the local Workgraph status check.
- Proved Garmin Connect readiness from the local governed Postgres sync:
  163 activities, 275 daily summaries, and latest daily summary sync
  `2026-05-17T18:23:58Z`.
- Promoted the deployed b-state Garmin index manifest to
  `backend=garmin_postgres`, `status=declared`.
- Proved b-state LFW federation access/freshness from deployed LFW read models.
- Promoted the deployed b-state LFW federation index manifest to declared.
- Regenerated b-state capability, preflight, freshness, understanding, and agent
  package read models. The final Samantha package was built at
  `2026-05-17T18:39:00Z` after the LFW company-layer refresh.
- Added `question_route.personal.small_consulting_firm_contacts`, backed by
  `tool.relationship_substrate.search_small_consulting_firm_contacts`, so
  Samantha can use enrichment-backed relationship-substrate search for smaller
  consulting/advisory/professional-services firm questions.
- Added Caroline's governed federated relationship-index route to
  `state_instance.acme_ops` with no local LFW source materialization.

## Current Agent Package Status

Caroline package:

- Package ID: `instance_agent_package.lfw.caroline`
- All sources are ready.
- Open questions: none.

Samantha package:

- Package ID: `instance_agent_package.acme_ops.samantha`
- Ready sources:
  - `connector.personal.folio`
  - `connector.personal.msgvault`
  - `connector.personal.agentmem`
  - `connector.personal.workboard`
  - `connector.personal.relationship_substrate`
  - `connector.personal.projects`
  - `connector.personal.garmin_connect`
  - `connector.personal.lfw_state_system`
- Remaining source gap:
  - `connector.personal.spotify` is usable as stale historical evidence from
    the assistant Postgres cache, but current Spotify API refresh remains
    blocked by OAuth `invalid_client`.

## Test Commands

From `/path/to/state-system`:

```bash
python3 -m state_system.cli --project-root . --state-root /path/to/state-system-runtime instance-agent-package-render instance_agent_package.lfw.caroline
python3 -m state_system.cli --project-root . --state-root /path/to/personal-state instance-agent-package-render instance_agent_package.acme_ops.samantha
```

## Follow-Up

Workgraph task `bstate-spotify-source-access-v0` owns the remaining Spotify
work. It should only close after real Spotify source access and a queryable
index are proven and Samantha's package no longer shows a Spotify gap.
