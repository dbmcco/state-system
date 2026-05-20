# High-Value Freshness Repair Loop

Date: 2026-05-18

## Summary

The repair loop is complete for package truthfulness. No source was marked
fresh without a source-owned evidence ref or explicit watermark. Caroline now
exposes Linear, GitHub, and transcript sources directly in the instance package
instead of hiding those gaps behind the interpreted LFW state source.

## Repairs

### LFW Linear

- Package source: `connector.lfw.linear`
- Access: `passed`
- Freshness: `fresh`
- Watermark: `linear.latest_updated_at:2026-05-15T19:38:27.710Z`
- Checked at: `2026-05-18T18:31:59Z`
- Evidence:
  - `paia:preflight:linear:company.lfw:20260518T183154Z`
  - `paia:freshness:linear:company.lfw:20260518T183159Z`
- Package gap: none.

### LFW GitHub

- Package source: `connector.lfw.github_org`
- Access: `passed`
- Freshness: `fresh`
- Watermark: `github.pushed_at:2026-05-15T19:35:42Z;repo:draftforge`
- Checked at: `2026-05-18T18:32:00Z`
- Evidence:
  - `paia:preflight:github:company.lfw:20260518T183155Z`
  - `paia:freshness:github:company.lfw:20260518T183200Z`
- Package gap: none.

### LFW Transcripts

- Raw transcript source: `connector.lfw.transcripts.raw`
- Raw access: `planned`
- Raw freshness: `fresh` as local path heartbeat only.
- Raw index: `planned`
- Raw gaps:
  - `gap.state_instance.lfw.connector.lfw.transcripts.raw.access_planned`
  - `gap.state_instance.lfw.connector.lfw.transcripts.raw.index_planned`

- Processed transcript source: `connector.lfw.transcripts.processed`
- Processed access: `planned`
- Processed freshness: `unknown`
- Processed index: `planned`
- Processed gaps:
  - `gap.state_instance.lfw.connector.lfw.transcripts.processed.access_planned`
  - `gap.state_instance.lfw.connector.lfw.transcripts.processed.freshness_unknown`
  - `gap.state_instance.lfw.connector.lfw.transcripts.processed.index_planned`

Transcript evidence remains unavailable for answers until the raw ingest and
processed document pipeline emit usable index/freshness records.

### Spotify

- Package source: `connector.personal.spotify`
- Access: `passed`
- Freshness: `stale`
- Historical cache watermark:
  `spotify.assistant_postgres.spotify_listening_records.played_at:2026-02-15T15:09:00Z`
- Live API blocker: `spotify:oauth_refresh:invalid_client:2026-05-17`

Spotify remains open because the repair requires a matching
`SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET` pair or a fresh OAuth run. The Sam
package correctly keeps `gap.state_instance.braydon_personal.connector.personal.spotify.freshness_stale`.

## Commands Run

Regenerated Caroline read model and package:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m state_system.cli \
  --project-root /Users/braydon/projects/experiments/state-system \
  --state-root /Users/braydon/projects/work/lfw/state-system \
  instance-understanding-surface-read \
  --output-dir /Users/braydon/projects/work/lfw/state-system/instance-understanding

PYTHONDONTWRITEBYTECODE=1 python3 -m state_system.cli \
  --project-root /Users/braydon/projects/experiments/state-system \
  --state-root /Users/braydon/projects/work/lfw/state-system \
  instance-agent-package-build \
  --instance-ref state_instance.lfw \
  --agent-ref agent.caroline \
  --persona-ref persona.caroline \
  --created-at 2026-05-18T21:25:00Z \
  --package-id instance_agent_package.lfw.caroline

PYTHONDONTWRITEBYTECODE=1 python3 -m state_system.cli \
  --project-root /Users/braydon/projects/experiments/state-system \
  --state-root /Users/braydon/projects/work/lfw/state-system \
  instance-agent-package-export \
  --output-dir /Users/braydon/projects/work/lfw/state-system/instance-agent-package
```

## Next Commands

Spotify live OAuth:

```bash
# In the b-state/PAIA runtime where Spotify sync is configured:
# 1. Restore or rotate matching SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.
# 2. Re-run Spotify OAuth.
# 3. Run the live Spotify sync.
# 4. Emit b-state instance preflight/freshness records with the new playback watermark.
# 5. Rebuild Samantha package.
```

Transcript pipeline:

```bash
# In the LFW source runtime:
# 1. Build or refresh raw transcript ingest for /Users/braydon/projects/work/lfw/transcripts.
# 2. Emit index.lfw.transcripts.raw readiness.
# 3. Build processed transcript read model.
# 4. Emit index.lfw.transcripts.processed readiness and freshness watermark.
# 5. Rebuild Caroline package.
```
