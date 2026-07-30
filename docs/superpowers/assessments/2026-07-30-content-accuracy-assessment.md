# Content Accuracy Assessment — Plan 2 Phase A

Date: 2026-07-30
Scope: product repo `/Users/braydon/projects/experiments/state-system` plus deployed roots:

- `lfw`: `/Users/braydon/projects/work/lfw/state-system`
- `synth`: `/Users/braydon/projects/work/synth/state-system`
- `b-state`: `/Users/braydon/projects/personal/b-state`
- `navicyte`: `/Users/braydon/projects/work/navicyte/navicyte-workspace/state-system`

Note: requested `plan.md` and `progress.md` were not present at `/Users/braydon/projects/experiments/state-system/` during this assessment (`read` returned ENOENT).

## Level definitions used here

- **L1 — recency evidence:** a record says a source/index/probe/package watermark was checked at a time, with status computed from stale-after policy. This does **not** by itself prove the record still matches the live source now.
- **L2 — correspondence evidence:** I independently re-derived the live/source/index watermark and compared it with the newest stored freshness record. For `source_index`/`derived_index`, L2 only covers the index or local metadata, not necessarily the remote corpus behind it.
- **L3 — semantic drift evidence:** a model or reviewer judges whether content/claims still mean what they used to mean. No connector freshness record currently attains L3 by itself.
- **`<L1 content` / unproven:** package generation, probe-only, declared-gap, or legacy missing-basis records that explicitly do not prove content freshness.

## 1. Primitive inventory

| Primitive | Level | What it actually proves | What it does not prove |
|---|---:|---|---|
| Freshness basis contract in `state_system/instance_source_freshness.py` | L1 | Enforces required fields, accepted `watermark_basis`, typed timestamps per basis, and non-conflation rules; it also stamps `freshness_is_recency_evidence=True`, `proves_live_access=False`, `authorizes_execution=False` (`state_system/instance_source_freshness.py:20-26`, `:58-91`, `:95-241`). | Does not re-query the live source at read time, compare stored watermark to live data, prove full corpus completeness, authorize actions, or judge semantic drift. |
| `RecordedStalenessReviewer` | L3, but replay-only | Replays a previously recorded model judgment for a matching staleness packet/scope/week and filters broader recordings to the requested findings (`state_system/staleness_runner.py:328-404`). | Does not create a new live judgment, verify the freshness record against the live source, or prove the recorded model output was correct today. |
| `RecordedStrategicReviewer` | L3, but replay-only | Replays a previously recorded model judgment for a strategic packet, using exact or same-scope prior-week routing (`state_system/strategic_staleness.py:644-701`). | Does not query live strategic sources or prove a claim still holds today; it depends on recorded model output. |
| `LiveStalenessReviewer` and `LiveStrategicReviewer` stubs | Potential L3; current implementation proves nothing without injection | They define the production hook: an injected `model_client.review(...)` with schema refs (`state_system/staleness_runner.py:407-433`, `state_system/strategic_staleness.py:704-729`). | With no injected client they raise `NotImplementedError`; they do not perform live source correspondence checks or run from the CLI by themselves. |
| `content_health` aggregation | L1 aggregation | Aggregates freshness statuses, expired stale-after refs, source gaps, and a staleness banner into package/content health (`state_system/content_health.py:33-87`, `:130-183`). | Does not inspect live sources, validate stored watermarks against live watermarks, or make semantic judgments. |
| Fleet refresh report-age canary | L1 producer/report recency | Compares a fleet-refresh report `checked_at` to independent wall-clock `as_of` and TTL; missing/unreadable/over-age reports fail (`state_system/fleet_refresh.py:535-628`). | Does not prove any connector watermark, source content, or semantic accuracy; it only catches frozen/missing reports. |
| Fleet `adapter_commands` runner | L1 runner evidence; can feed L2 if adapter is re-run in compare mode | Executes declared adapter commands, records pass/fail/stdout/stderr, then rebuilds read models/packages (`state_system/fleet_refresh.py:221-328`, `:331-378`). | The runner itself does not know connector semantics and does not re-derive-and-diff; current deployed shell scripts primarily record new freshness evidence. |
| `state_system/source_adapters.py` | L2 for local git metadata only | Reads local git commit metadata and converts it into normalized source events with idempotency and `sync_context.source_watermark` (`state_system/source_adapters.py:9-64`, `:67-95`). | It is not a general connector adapter layer, does not read MsgVault/Folio/Drive/etc., does not write freshness records, and does not compare stored records with live watermarks. |
| API inspect surface in `api_surface.py` | L1 inspection surface | `inspect` reads a package and returns package/content/process health, source gaps, expired freshness refs, acknowledgements, and repair action names (`state_system/api_surface.py:94-110`, `:159-202`). | Does not refresh or validate live sources; unsupported `refresh/search/record` return partial “requires a source-specific adapter” messages (`state_system/api_surface.py:138-147`). |

## 2. Per-connector accuracy map

### Counts by root

| Root | Connectors/source scopes assessed | L2 current correspondence | L1 recorded recency only | L3 semantic drift | `<L1 content` / unproven |
|---|---:|---:|---:|---:|---:|
| lfw | 9 | 4 | 3 | 0 | 2 |
| synth | 9 | 6 | 1 | 0 | 2 |
| b-state | 20 | 4 | 12 | 0 | 4 |
| navicyte | 6 | 2 | 2 | 0 | 2 |
| **Total** | **44** | **16** | **18** | **0** | **10** |

### `lfw`

| Connector | Source | Basis | Recorded watermark | checked_at | status | Accuracy level and why |
|---|---|---|---|---|---|---|
| `connector.lfw.folio` | `folio:tenant:lfw` | `source_content` | `folio.latest_note_updated_at:2026-07-15T17:28:44Z;notes=403` | 2026-07-30T13:44:28Z | stale | **L2**: live Folio notes matched updated_at and count; stale means policy age, not mismatch. |
| `connector.lfw.github_org` | `github:org:LightForge-Works` | `source_event` | `github.org.latest_repo_commit_at:2026-07-29T14:31:35Z;latest_repo:LightForge-Works/lfw-process:2026-07-29T14:31:35Z` | 2026-07-29T17:02:06Z | fresh | **L2**: `gh repo list LightForge-Works` returned the same latest repo/pushedAt. |
| `connector.lfw.linear` | `linear:teams:FORGE,INT` | `source_event` | `linear.checked_at:2026-07-30T13:44:28Z;latest_updated_at:2026-07-21T21:41:18Z;teams:FORGE:FORGE-208:2026-07-21T21:41:18.942Z,INT:INT-322:2026-06-16T15:04:42.188Z` | 2026-07-30T13:44:28Z | stale | **L1**: record proves a Linear metadata query was recorded; I did not re-query Linear because it requires API credentials and external service access. |
| `connector.lfw.msgvault` | `msgvault:tenant:lfw-email` | `source_content` | `msgvault.latest_sent_at:2026-07-29T16:38:59Z;messages=3650;account=braydon@lightforgeworks.com` | 2026-07-29T17:02:06Z | fresh | **L1 today**: live MsgVault now reports `2026-07-30T13:36:32Z;messages=3665`, so the stored record no longer corresponds to current live source. |
| `connector.lfw.state_system` | `state-system-instance:state_instance.lfw` | `package_generation` | `state_system.package_generated_at:2026-07-29T17:02:06Z` | 2026-07-29T17:02:06Z | unknown | **<L1 content**: package/process recency only; contract explicitly says package generation does not prove underlying corpus freshness. |
| `connector.lfw.transcripts.processed` | `transcripts:pipeline:lfw` | `derived_index` | `transcripts.processed.read_model_mtime:2026-05-20T22:55:28Z` | 2026-07-29T17:02:06Z | stale | **L2-index**: file mtime matched; only proves derived transcript read-model mtime. |
| `connector.lfw.transcripts.raw` | `local:/Users/braydon/projects/work/lfw` | `source_index` | `local.transcripts.raw_index_mtime:2026-05-20T22:55:28Z` | 2026-07-29T17:02:06Z | stale | **L2-index**: raw index file mtime matched; does not prove full transcript corpus accuracy. |
| `connector.lfw.transcripts.raw` | `local:/Users/braydon/projects/work/lfw/transcripts` | missing legacy basis | `local.transcripts.raw_index_mtime:2026-05-20T22:55:28Z` | 2026-06-04T20:14:05Z | fresh | **<L1 content**: legacy record lacks `watermark_basis`; it would fail the current contract. |
| `connector.lfw.zulip` | `zulip:realm:lightforgeworks` | `source_event` | `zulip.latest_message:1384@2026-07-29T16:38:26Z` | 2026-07-29T17:02:06Z | fresh | **L1**: metadata event was recorded; I did not re-query Zulip because it requires realm credentials. |

### `synth`

| Connector | Source | Basis | Recorded watermark | checked_at | status | Accuracy level and why |
|---|---|---|---|---|---|---|
| `connector.synthyra.docs.transcripts` | `transcripts:pipeline:synthyra` | `source_content` | `transcripts.local.latest_mtime:2025-11-05T19:10:06Z;files=11` | 2026-07-30T13:45:31Z | stale | **L2**: local transcript corpus mtime and file count matched. |
| `connector.synthyra.drive` | `gws:mcco:drive:synthyra-corpus-search` | `source_index` | `synthyra.sync_state_mtime:2026-07-01T14:27:36Z` | 2026-07-30T13:45:31Z | fresh | **L2-index**: local sync-state mtime matched; does not prove remote Drive corpus freshness. |
| `connector.synthyra.drive` | `gws:mcco:shared-drive:Synthyra Shared` | missing legacy basis | `unverified:gws-drive-live-check-not-run` | 2026-05-18T17:12:00Z | unknown | **<L1 content**: legacy unverified record; cannot cleanly rederive from declared data. |
| `connector.synthyra.folio` | `folio:tenant:synthyra` | `source_content` | `folio.latest_note_updated_at:2026-06-30T20:14:17Z;notes=958;query_results=5` | 2026-07-30T13:45:31Z | stale | **L2**: live Folio matched updated_at and note count; `query_results` was not part of my independent notes endpoint check. |
| `connector.synthyra.local` | `local:/Users/braydon/projects/work/synth` | `probe_only` | `local.latest_mtime:/Users/braydon/projects/work/synth/sync/state.json@2026-07-01T14:27:36Z` | 2026-07-30T13:45:31Z | unknown | **<L1 content**: probe-only record states full local corpus watermark is unproven. |
| `connector.synthyra.msgvault` | `msgvault:tenant:synthyra-email` | `source_content` | `msgvault.latest_sent_at:2026-07-29T15:35:55Z;messages=1285;account=braydon@synthyra.com` | 2026-07-29T17:01:07Z | fresh | **L1 today**: live MsgVault now reports `2026-07-30T13:31:58Z;messages=1289`, so current correspondence fails. |
| `connector.synthyra.repo.atlas` | `github:repo:Synthyra/atlas` | `source_event` | `repo.last_commit_at:2026-07-21T16:24:21Z;remote:https://github.com/Synthyra/atlas.git` | 2026-07-29T17:01:07Z | stale | **L2**: `gh repo view Synthyra/atlas --json pushedAt` matched. Local checkout lags, so local git alone is not a clean proxy for remote. |
| `connector.synthyra.repo.decks` | `github:repo:Synthyra/synthyra-decks` | `source_event` | `repo.last_commit_at:2026-07-08T23:02:06Z;remote:https://github.com/Synthyra/synthyra-decks.git` | 2026-07-29T17:01:07Z | stale | **L2**: `gh repo view` matched remote pushedAt. |
| `connector.synthyra.repo.org_workspace` | `github:repo:Synthyra/synthyra-ai-org` | `source_event` | `repo.last_commit_at:2026-07-21T12:13:58Z;remote:https://github.com/Synthyra/synthyra-ai-org.git` | 2026-07-29T17:01:07Z | stale | **L2**: `gh repo view` matched remote pushedAt. |

### `b-state`

| Connector | Source | Basis | Recorded watermark | checked_at | status | Accuracy level and why |
|---|---|---|---|---|---|---|
| `connector.personal.agentmem` | `agentmem:tenant:braydon` | `source_content` | `agentmem.paia_memory.latest_updated_at:2026-03-25T15:54:43Z;tenant=braydon;facets=6` | 2026-07-29T17:01:35Z | stale | **L2**: PAIA memory `braydon` facet count/latest updated_at matched. |
| `connector.personal.beeper.imessage` | Beeper iMessage SQLite | `declared_gap` | `beeper.imessage.account_state:enabled;threads=1;messages=0` | 2026-07-30T13:14:55Z | unknown | **<L1 content**: account/index readability gap is declared; no message timestamp exists to prove source freshness. |
| `connector.personal.beeper.whatsapp` | Beeper WhatsApp SQLite | `source_index` | `beeper.whatsapp.local_index.latest_thread_timestamp:2026-07-30T13:13:02Z;threads=87;freshness_basis=beeper_local_index_fresh;source_sync_watermark=unproven` | 2026-07-30T13:14:55Z | fresh | **L1-index today**: local SQLite now reports `2026-07-30T13:36:04Z;threads=87`; source sync watermark remains unproven. |
| `connector.personal.blog` | `blog:local:/Users/braydon/projects/dbmcco.github.io` | `source_content` | `blog.latest_post_mtime:2026-07-17T09:42:50Z;posts=207` | 2026-07-30T13:14:55Z | fresh | **L2**: local `_posts` mtime and post count matched. |
| `connector.personal.folio` | `folio:tenant:personal` | `source_content` | `folio.latest_note_updated_at:2026-07-29T16:51:34Z;notes=2000` | 2026-07-30T13:14:55Z | fresh | **L2**: live Folio default tenant matched updated_at and count. |
| `connector.personal.garmin_connect` | `garmin-connect:account:braydon` | `source_index` | `garmin.checked_at:2026-07-30T13:14:55Z;daily_synced_at:2026-07-30T12:15:52Z;activity_synced_at:2026-07-14T21:30:33Z;latest_activity_at:2026-07-14T19:27:38Z;daily_rows:47;activity_rows:255` | 2026-07-30T13:14:55Z | fresh | **L1-index**: local sync database watermark was recorded; I did not rederive because it requires the Garmin sync DB env. |
| `connector.personal.lfw_state_system` | `state-system-instance:state_instance.lfw` | `package_generation` | `state_system_instance.lfw.generated_at:2026-07-29T16:28:57Z;requires_refresh_before_external_action=true;expired_freshness_refs=4` | 2026-07-29T17:01:35Z | unknown | **<L1 content**: federated package metadata, not raw LFW source accuracy. |
| `connector.personal.msgvault` | `msgvault:tenant:personal-email` | `source_content` | aggregate latest `2026-07-29T16:38:59Z`; 125709 messages; one stale account listed | 2026-07-29T17:01:35Z | stale | **L1 today**: spot-checked accounts have advanced in live MsgVault; aggregate status also intentionally folds in stale account watermarks. |
| `connector.personal.msgvault.account` | `msgvault:account:b@aclara.us` | `source_content` | `2026-07-28T20:43:11Z;messages=8799` | 2026-07-29T17:01:35Z | fresh | **L1**: per-account watermark recorded; not spot-checked. |
| `connector.personal.msgvault.account` | `msgvault:account:b@mcco.us` | `source_content` | `2026-07-29T16:38:44Z;messages=21436` | 2026-07-29T17:01:35Z | fresh | **L1 today**: live MsgVault now reports `2026-07-30T13:48:48Z;messages=21522`. |
| `connector.personal.msgvault.account` | `msgvault:account:braydon@intempio.us` | `source_content` | `2026-07-02T14:08:41Z;messages=86075` | 2026-07-29T17:01:35Z | stale | **L1**: stale per-account watermark recorded; not rederived. |
| `connector.personal.msgvault.account` | `msgvault:account:braydon@lightforgeworks.com` | `source_content` | `2026-07-29T16:38:59Z;messages=3650` | 2026-07-29T17:01:35Z | fresh | **L1 today**: same live account as LFW has advanced to `2026-07-30T13:36:32Z;messages=3665`. |
| `connector.personal.msgvault.account` | `msgvault:account:braydon@synthyra.com` | `source_content` | `2026-07-29T15:35:55Z;messages=1285` | 2026-07-29T17:01:35Z | fresh | **L1 today**: same live account as Synthyra has advanced to `2026-07-30T13:31:58Z;messages=1289`. |
| `connector.personal.msgvault.account` | `msgvault:account:braydonjm@gmail.com` | `source_content` | `2026-07-28T21:00:45Z;messages=4464` | 2026-07-29T17:01:35Z | fresh | **L1**: per-account watermark recorded; not spot-checked. |
| `connector.personal.paia_memory.owner` | `paia-memory:tenant:braydon` | `source_content` | `paia_memory.latest_updated_at:2026-03-25T15:54:43Z;tenant=braydon;facets=6` | 2026-07-29T17:01:35Z | stale | **L2**: PAIA memory `braydon` facet count/latest updated_at matched. |
| `connector.personal.paia_memory.samantha` | `paia-memory:tenant:Samantha` | `source_content` | `paia_memory.latest_updated_at:2026-07-29T04:05:24Z;tenant=Samantha;facets=41` | 2026-07-29T17:01:35Z | fresh | **L1 today**: live PAIA memory now reports `2026-07-30T04:04:20Z;facets=41`. |
| `connector.personal.projects` | `local:/Users/braydon/projects/personal` | `probe_only` | `local.projects.root_mtime:2026-07-06T17:01:41Z;corpus_watermark=unproven` | 2026-07-29T17:01:35Z | unknown | **<L1 content**: probe-only; recursive project corpus freshness explicitly unproven. |
| `connector.personal.relationship_substrate` | `relationship-substrate:default` | `source_content` | latest interaction `2026-07-29T16:38:59Z`; latest person/org around `2026-07-29T17:00Z` | 2026-07-29T17:01:35Z | fresh | **L1 today**: live Postgres now reports latest interaction/person/org on 2026-07-30, so stored record no longer corresponds to current source. |
| `connector.personal.spotify` | `spotify:account:braydon` | `source_content` | `spotify.assistant_postgres.spotify_listening_records.played_at:2026-02-15T15:09:00Z;live_oauth_status=auth_blocked;oauth_error=invalid_client` | 2026-06-23T01:39:00Z | stale | **L1**: old local/Postgres watermark plus auth failure; cannot cleanly rederive live Spotify due OAuth failure encoded in the record. |
| `connector.personal.workboard` | `paia-workboard:default` | `probe_only` | `paia_workboard.wg_status_checked_at:2026-07-29T17:01:35Z;corpus_watermark=unproven` | 2026-07-29T17:01:35Z | unknown | **<L1 content**: Workgraph command execution only; no Workboard corpus watermark. |

### `navicyte`

| Connector | Source | Basis | Recorded watermark | checked_at | status | Accuracy level and why |
|---|---|---|---|---|---|---|
| `connector.navicyte.drive` | `gws:mcco:shared-drive:navicyte-biotechnologies` | `source_index` | `navicyte.sync_state_mtime:2026-07-25T14:41:17Z` | 2026-07-30T13:44:47Z | fresh | **L2-index**: local sync-state mtime matched; does not prove remote Drive corpus watermark. |
| `connector.navicyte.folio` | `folio:tenant:navicyte` | `source_content` | `folio.latest_note_updated_at:2026-07-29T20:31:47Z;notes=408;query_results=5` | 2026-07-30T13:44:47Z | fresh | **L1 today**: live Folio now reports `2026-07-30T13:58:06Z;notes=408`, so current correspondence fails. |
| `connector.navicyte.local` | `local:/Users/braydon/projects/work/navicyte` | `probe_only` | `local.latest_mtime:/Users/braydon/projects/work/navicyte/sync/state.json@2026-07-25T14:41:17Z` | 2026-07-30T13:44:47Z | unknown | **<L1 content**: probe-only; full local corpus watermark unproven. |
| `connector.navicyte.msgvault` | `msgvault:tenant:navicyte-email` | `source_content` | `msgvault.latest_sent_at:2026-07-29T16:38:44Z;messages=21436;account=b@mcco.us` | 2026-07-29T17:01:22Z | fresh | **L1 today**: live MsgVault now reports `2026-07-30T13:48:48Z;messages=21522`. |
| `connector.navicyte.repo` | `github:repo:Navicyte/navicyte-workspace` | `source_event` | `repo.last_commit_at:2026-07-25T14:49:14Z;updated_at:2026-07-25T14:49:42Z;remote:https://github.com/Navicyte/navicyte-workspace` | 2026-07-30T13:44:47Z | stale | **L2**: `gh repo view Navicyte/navicyte-workspace` matched remote pushedAt/updatedAt. |
| `connector.navicyte.state_system` | `state-system-instance:state_instance.navicyte` | `package_generation` | `state_system.package_generated_at:2026-07-29T17:01:22Z` | 2026-07-29T17:01:22Z | unknown | **<L1 content**: package/process recency only. |

## Live-vs-recorded spot checks

These were read-only checks against local services, local files, local git, or `gh` read APIs.

| Check | Result |
|---|---|
| Folio LFW | match: recorded/live `2026-07-15T17:28:44Z;notes=403`. |
| Folio Synthyra | match on latest/count: recorded `2026-06-30T20:14:17Z;notes=958;query_results=5`; live `2026-06-30T20:14:17Z;notes=958`. |
| Folio personal | match: `2026-07-29T16:51:34Z;notes=2000`. |
| Folio Navicyte | mismatch/current advanced: recorded `2026-07-29T20:31:47Z`; live `2026-07-30T13:58:06Z`. |
| MsgVault LFW account | mismatch/current advanced: recorded `2026-07-29T16:38:59Z;3650`; live `2026-07-30T13:36:32Z;3665`. |
| MsgVault Synthyra account | mismatch/current advanced: recorded `2026-07-29T15:35:55Z;1285`; live `2026-07-30T13:31:58Z;1289`. |
| MsgVault Navicyte / b@mcco.us | mismatch/current advanced: recorded `2026-07-29T16:38:44Z;21436`; live `2026-07-30T13:48:48Z;21522`. |
| GitHub LightForge-Works org | match: `gh repo list` reported `LightForge-Works/lfw-process` pushed at `2026-07-29T14:31:35Z`. |
| GitHub Synthyra repos | match: `gh repo view` pushedAt matched `atlas=2026-07-21T16:24:21Z`, `synthyra-ai-org=2026-07-21T12:13:58Z`, `synthyra-decks=2026-07-08T23:02:06Z`. |
| GitHub Navicyte repo | match: `gh repo view` pushedAt/updatedAt matched `2026-07-25T14:49:14Z` / `2026-07-25T14:49:42Z`. |
| Local Drive sync-state mtimes | match for Synthyra `2026-07-01T14:27:36Z` and Navicyte `2026-07-25T14:41:17Z`. |
| Local transcript/blog mtimes | match for LFW raw/processed transcript indexes `2026-05-20T22:55:28Z`, Synthyra transcripts `2025-11-05T19:10:06Z;files=11`, and blog posts `2026-07-17T09:42:50Z;posts=207`. |
| Beeper WhatsApp local index | mismatch/current advanced: recorded latest thread `2026-07-30T13:13:02Z`; live SQLite latest thread `2026-07-30T13:36:04Z`; source sync watermark remains unproven. |
| PAIA memory | `braydon` matched `2026-03-25T15:54:43Z;facets=6`; `Samantha` advanced from recorded `2026-07-29T04:05:24Z` to live `2026-07-30T04:04:20Z;facets=41`. |
| Relationship substrate | mismatch/current advanced: recorded latest interaction/person/org were 2026-07-29; live Postgres reports latest interaction `2026-07-30T10:55:12Z`, person `2026-07-30T11:13:04Z`, org `2026-07-30T11:12:56Z`. |

## Connectors not cleanly re-derived here

- **Linear**: requires a Linear API token and external GraphQL request. The deployed script has a clear query path, but I did not use credentials for this read-only assessment.
- **Zulip**: requires Zulip realm credentials loaded from a private env file.
- **Garmin Connect**: current record is from a local sync database whose connection string is loaded from a separate Garmin sync `.env`; not checked here.
- **Spotify**: record itself says live OAuth is blocked (`invalid_client`), so live source correspondence cannot be re-derived cleanly.
- **Package-generation/state-system-instance connectors**: only package metadata can be read locally; that cannot prove upstream source content accuracy.
- **Probe-only connectors** (`local`, `projects`, `workboard`) and **declared gaps** (Beeper iMessage): by design state that source/corpus watermark is unproven.
- **Remote Drive corpus**: local sync-state mtimes are cheaply re-derivable, but they prove the local sync/index timestamp, not newest remote Drive document timestamp.

## 3. Gap analysis

For **“fresh” to mean “verified accurate”** instead of “checked recently,” the system would need all of the following:

1. A declared read-only derivation function per connector that returns a normalized live watermark and item count using the same semantics as the freshness record.
2. A compare step that reads the newest stored freshness record by `(instance_ref, connector_ref, source_ref)` and diffs stored watermark/status against the live-derived watermark/status.
3. A result contract that distinguishes “record was fresh when written” from “record corresponds to live source now.”
4. Corpus-level completeness evidence where counts matter; `max(timestamp)` alone cannot prove no missing records unless paired with counts/cursors and source-specific invariants.
5. Optional L3 review only after L2 passes, because semantic drift judgments need trustworthy source evidence.

The closest existing primitive with least new code is **the deployed fleet-refresh adapter scripts**, not `state_system/source_adapters.py`. The scripts already know how to read MsgVault, Folio, local files, GitHub, Beeper, PAIA memory, etc., and produce normalized watermarks. However, today they are recorders invoked through `fleet_refresh._run_adapter_command`; they do not expose a read-only “derive and print watermark JSON” mode or a product-level diff API.

`state_system/source_adapters.py` can be reused for **Git local commit metadata only**. It is not currently a general re-derive-and-diff read path for Plan 2 B1.

### B1 straightforwardness

**B1 is straightforward but not zero-code.** The low-risk path is:

- Factor each deployed shell probe into `derive` (read-only JSON output) and `record` (current behavior) modes.
- Add a generic comparator that loads the newest freshness record and compares normalized fields: `watermark_basis`, primary timestamp, item count, stale-after policy result, and status.
- Surface correspondence as a separate L2 field, e.g. `correspondence_status: matched|advanced|regressed|unknown|unproven`, without mutating the original L1 record.

The live spot checks show this would immediately add value: several records marked `fresh` by their last run are no longer current relative to live MsgVault/Folio/Beeper/PAIA/relationship data.

## Concise findings summary

- **No L3 connector accuracy exists today.** L3 is only available through recorded/live reviewer paths, not through freshness records.
- **Current L2 coverage is patchy:** 16 of 44 source scopes were independently matched in this assessment, mostly Folio, GitHub, local files, local sync-state/index mtimes, and selected memory records.
- **Fresh does not mean live-current:** MsgVault LFW/Synthyra/Navicyte, Navicyte Folio, Beeper WhatsApp, Samantha memory, and relationship substrate had live watermarks newer than their stored “fresh” records.
- **Source adapters are not the B1 answer by themselves:** `source_adapters.py` only covers local git event extraction. The deployed fleet-refresh scripts are the reusable connector knowledge, but need a read-only derive/diff mode.
