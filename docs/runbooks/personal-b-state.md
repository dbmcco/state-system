# Personal b-state Runbook

Operational runbook for Braydon's personal State System instance
(`state_instance.braydon_personal`, runtime root
`/Users/braydon/projects/personal/b-state`).

This document is operator-facing. It is not a design spec. For why the instance
exists and how it differs from a company instance, read `docs/NORTH_STAR.md` and
`docs/decisions/2026-05-16-state-instance-entity-and-federated-indexes.md`.

## What This Instance Is

`state_instance.braydon_personal` is one deployed State System instance. The
product repo (this repo, `experiments/state-system`) ships schemas, contracts,
and CLI; the personal instance owns the runtime artifacts under
`/Users/braydon/projects/personal/b-state`. Nothing in this runbook should be
read as company state, and nothing in a company runbook should be read as
personal state.

The declared capability pack lives in
`examples/instance-capability/instance-braydon-personal.json` and is what every
command below resolves against.

## Vector Stores: Source-Owned Indexes Plus Catalog

The personal instance does not run one giant vector store. Each source system
owns its own raw index; the instance owns a catalog and (eventually) an
interpreted-state index over evidence and claims.

Source-owned raw indexes (declared in `index_manifests`):

| Index ref | Backend | Owner | Status |
|---|---|---|---|
| `index.personal.folio.corpus` | `postgres_pgvector` | folio | declared |
| `index.personal.msgvault.email` | `msgvault_sqlite_vec` | msgvault | declared |
| `index.personal.agentmem.memory` | `postgres_pgvector` | agentmem | declared |
| `index.personal.workboard.tasks` | `workgraph_jsonl` | paia_runtime | declared |
| `index.personal.relationship_substrate.network` | `postgres_pgvector` | relationship_substrate | declared |
| `index.personal.projects.local_metadata` | `local_path_metadata` | local filesystem | declared |
| `index.personal.garmin_connect.activity` | `garmin_postgres` | Garmin local sync | declared |
| `index.personal.spotify.listening` | `assistant_postgres_spotify_history` | historical Spotify cache | declared, stale |

State System-owned indexes:

| Index ref | Backend | Scope | Status |
|---|---|---|---|
| `index.personal.state_system.interpreted` | `postgres_pgvector` | interpreted_state_index | planned |
| `index.personal.lfw_state_system.interpreted` | `state_system_remote` | interpreted_state_index over LFW | planned |

The instance capability pack is the routing/catalog layer. The understanding
surface is the consumer-facing read model that lists which indexes are
addressable today, what backend each one uses, and which `query_surface` to
call. Do not query a raw source index "through" State System; query the source
system directly (or its `tool_ref`) and cite the evidence in State System
records. State System does not copy raw corpora.

## Connector Boundaries

Each declared connector is owned by another system. The personal instance
federates; it does not absorb.

- **`connector.personal.folio` (folio)** — Folio at
  `/Users/braydon/projects/experiments/folio` owns notes, daily entries, and its
  pgvector corpus. b-state preflight only checks that the folio root exists
  (`local_path` mechanical check); reads happen through `tool.paia.folio.search`
  or the `folio` CLI. Do not write to folio from b-state code paths.
- **`connector.personal.msgvault` (msgvault)** — msgvault at
  `/Volumes/data2/msgvault` owns the email archive and its sqlite-vec index.
  b-state records freshness only; it never ingests messages. Treat msgvault as
  read-only. Live search uses the `msgvault` MCP server or the CLI documented in
  `experiments/CLAUDE.md`.
- **`connector.personal.agentmem` (agentmem)** — agentmem owns Braydon's
  personal agent memory (`agentmem:tenant:braydon`). b-state cites agentmem
  evidence; it does not store agent memory. Promotion of agent memory into
  durable shared state happens through governed proposals, not by copying memory
  rows.
- **`connector.personal.workboard` (paia_workboard)** — Workgraph
  (`paia-workboard:default`) is the operational task store. b-state surfaces
  task state as evidence; it does not own task lifecycle. Use `wg` CLI or
  `tool.paia.workboard.read` for queries.
- **`connector.personal.relationship_substrate` (relationship_substrate)** —
  Relationship Substrate owns identity resolution, the relationship graph, and
  relationship operating pictures. It also owns subject-level relationship
  context notes for explicit user corrections such as "Patrick is my
  accountant, not a good fit for this search" or "this company is only relevant
  for finance-specific advisory questions." b-state federates and promotes
  selected evidence through governed proposals. Do not duplicate person/org
  records in b-state. Runtime reads use
  `tool.relationship_substrate.operating_picture` through Samantha's
  `relationship_substrate` tool. Enrichment-backed searches for contacts at
  smaller consulting, advisory, and professional-services firms use
  `tool.relationship_substrate.search_small_consulting_firm_contacts`. Use
  `tool.relationship_substrate.record_subject_note` for durable source-owned
  corrections and interpret returned subject notes as context-specific
  relationship evidence, not canonical profile facts or broad hidden filters.
- **`connector.personal.lfw_state_system` (state_system_instance)** — The LFW
  work instance at `/Users/braydon/projects/work/lfw/state-system` is itself a
  State System instance. b-state may read its interpreted state (e.g. an
  operating picture) subject to `governance.lfw.read_summary`. Cross-instance
  reads must preserve the source instance's governance. b-state does not
  inherit LFW connectors or LFW-only freshness rules.
- **`connector.personal.projects` (local_path)** — Bounded read surface over
  `/Users/braydon/projects/personal`. Used for project-root metadata only.
- **`connector.personal.garmin_connect` (garmin_connect)** — Declared through
  the governed local Garmin Postgres sync. Freshness records carry the latest
  source watermark; do not copy raw activity data into b-state.
- **`connector.personal.spotify` (spotify)** — Historical listening records are
  queryable in the old assistant Postgres cache. Treat them as usable stale
  evidence only. Live Spotify API refresh remains blocked until matching current
  OAuth app credentials are restored or the account completes OAuth again.

## Refresh Commands

All commands below are run from this repo
(`/Users/braydon/projects/experiments/state-system`) and target the personal
runtime root with `--state-root /Users/braydon/projects/personal/b-state`.

Replace timestamps with the current UTC time; `--stale-after` is typically 15
minutes to 1 hour after `--checked-at`.

### Preflight (proves live access only)

Record a preflight result for a connector:

```bash
python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-preflight-record \
  --preflight-ref preflight.state_instance.braydon_personal.connector.personal.folio \
  --instance-ref state_instance.braydon_personal \
  --connector-ref connector.personal.folio \
  --source-ref folio:tenant:personal \
  --connector-type folio \
  --status passed \
  --checked-at 2026-05-17T10:25:00Z \
  --stale-after 2026-05-17T10:40:00Z \
  --evidence-ref local-path:/Users/braydon/projects/experiments/folio
```

Run the non-destructive preflight runner across declared connectors:

```bash
python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-preflight-run \
  --instance-ref state_instance.braydon_personal \
  --checked-at 2026-05-17T10:25:00Z \
  --stale-after 2026-05-17T10:40:00Z
```

In v0 the runner only mechanically proves `local_path` connectors. Delegated
connectors (folio, msgvault, agentmem, workboard, relationship_substrate,
state_system_instance, garmin_connect, spotify) record as `planned` unless an
adapter or explicit target metadata is declared. `passed` sets
`proves_live_access: true`; `planned` keeps the connector visible as a declared
access gap.

### Source Freshness (recency evidence only)

```bash
python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-source-freshness-record \
  --instance-ref state_instance.braydon_personal \
  --connector-ref connector.personal.msgvault \
  --source-ref msgvault:tenant:personal-email \
  --connector-type msgvault \
  --status unknown \
  --checked-at 2026-05-17T10:15:00Z \
  --source-watermark msgvault.sync_status:unknown \
  --stale-after 2026-05-17T10:30:00Z \
  --evidence-ref paia:freshness:msgvault:unknown \
  --index-ref index.personal.msgvault.email \
  --index-owner source_system \
  --index-backend msgvault_sqlite_vec
```

`--status` is one of `fresh`, `stale`, `unknown`. `--index-*` flags attach the
source-owned index manifest to the freshness record so the understanding
surface can show "which raw index is behind this evidence".

### Export Read Models

```bash
python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-preflight-export \
  --output-dir /Users/braydon/projects/personal/b-state/instance-preflight

python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-source-freshness-export \
  --output-dir /Users/braydon/projects/personal/b-state/instance-source-freshness
```

## Read Commands

### Instance Understanding Surface

The consumer-facing read model that joins capability pack, preflight, freshness,
federation, and index metadata:

```bash
python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-understanding-surface-read \
  --output-dir /Users/braydon/projects/personal/b-state/instance-understanding
```

Output: `instance-understanding/instance-understanding-surface-read-model.json`.

### Instance Agent Package

Build a persona-bounded package over the instance:

```bash
python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-agent-package-build \
  --instance-ref state_instance.braydon_personal \
  --agent-ref persona.samantha \
  --created-at 2026-05-17T11:00:00Z \
  --review-goal "Surface current personal commitments and open loops."
```

Then export or render:

```bash
python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-agent-package-export \
  --output-dir /Users/braydon/projects/personal/b-state/instance-agent-package

python3 -m state_system.cli --project-root . \
  --state-root /Users/braydon/projects/personal/b-state \
  instance-agent-package-render <package_id>
```

## Output Locations

Runtime artifacts live under `/Users/braydon/projects/personal/b-state`:

```
/Users/braydon/projects/personal/b-state
├── state/                                  # File-backed stores (instance-capabilities, instance-preflight-results, instance-source-freshness, instance-agent-packages)
├── instance-capability/                    # instance-capability-read-model.json
├── instance-preflight/                     # instance-preflight-results-read-model.json
├── instance-source-freshness/              # instance-source-freshness-read-model.json
├── instance-understanding/                 # instance-understanding-surface-read-model.json
└── instance-agent-package/                 # instance-agent-packages-read-model.json
```

The `state/` tree is the source of truth (append-only JSON stores). The other
directories are exported read models — safe to delete and regenerate.

## Verification

After a refresh cycle, confirm each acceptance gate:

1. **Capability pack present**

   ```bash
   jq '.instances[] | select(.instance_ref=="state_instance.braydon_personal") | {id, source_connectors: (.source_connectors|length), index_manifests: (.index_manifests|length)}' \
     /Users/braydon/projects/personal/b-state/instance-capability/instance-capability-read-model.json
   ```

2. **Preflight has at least one `passed` connector**

   ```bash
   jq '.results[] | select(.instance_ref=="state_instance.braydon_personal") | {connector_ref, status, proves_live_access}' \
     /Users/braydon/projects/personal/b-state/instance-preflight/instance-preflight-results-read-model.json
   ```

3. **Freshness records cite an index_ref**

   ```bash
   jq '.records[] | {connector_ref, status, index_refs}' \
     /Users/braydon/projects/personal/b-state/instance-source-freshness/instance-source-freshness-read-model.json
   ```

4. **Understanding surface joins them**

   ```bash
   jq '.connectors[] | {connector_ref, preflight_status: .preflight.status, freshness_status: .freshness.status}' \
     /Users/braydon/projects/personal/b-state/instance-understanding/instance-understanding-surface-read-model.json
   ```

5. **Smoke tests pass for the instance surfaces**

   ```bash
   python3 -m unittest tests/test_instance_capability_pack.py \
     tests/test_instance_preflight_results.py \
     tests/test_instance_source_freshness.py \
     tests/test_instance_understanding_surface.py \
     tests/test_instance_agent_packages.py \
     tests/test_instance_federation.py
   ```

## Troubleshooting

- **Preflight runner records everything as `planned`.** Expected for delegated
  connectors in v0. Only `local_path` connectors prove mechanically. Use
  `instance-preflight-record` to record a `passed` result once you have
  out-of-band evidence (e.g. you confirmed msgvault MCP responded).
- **Freshness status `unknown` for msgvault.** msgvault does not expose a sync
  watermark surface yet. Record `unknown` with the real `checked_at`; do not
  fabricate a `fresh` watermark.
- **Understanding surface missing a connector.** It is filtered to the
  capability pack. If a connector is missing, edit
  `examples/instance-capability/instance-braydon-personal.json` and reseed; do
  not patch the runtime store directly.
- **Cross-instance read against LFW fails.** b-state honors LFW governance
  (`governance.lfw.read_summary`). If the LFW instance has not declared a
  read-summary surface, that is an LFW-side issue, not a b-state issue.
- **Garmin/Spotify show as access gaps.** Correct. Both are `planned`. They
  must not be cited as live evidence.
- **State directory looks empty after `state-root-migrate`.** The command is
  copy-not-destructive; the original path becomes a compatibility symlink to the
  new canonical root. Inspect the target path, not the legacy path.
- **Mixing personal and work runs.** Always set
  `--state-root /Users/braydon/projects/personal/b-state` for personal commands.
  LFW commands target `/Users/braydon/projects/work/lfw/state-system`. Wrong
  root produces silently empty exports.
