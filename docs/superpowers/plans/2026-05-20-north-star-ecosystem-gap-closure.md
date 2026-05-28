# North Star Ecosystem Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the operational source-readiness gaps exposed by the schema-backed North Star ecosystem run, then produce a readable North Star answer that remains grounded, gap-visible, and non-executing.

**Architecture:** Treat `north-star-answer.json` as the canonical read substrate. Repair source readiness inside each deployed state root with explicit preflight/freshness/index records, regenerate instance packages, rerun the ecosystem North Star check, then add a deterministic renderer over the JSON artifact. Work is split by instance and product surface so dirty runtime roots and product repo changes do not collide.

**Tech Stack:** Python `state_system.cli`, JSON schemas/read models, file-backed state roots, `jq`, `gh`, `gws-account`, `msgvault`, SQLite, existing fleet-refresh scripts, `unittest`.

---

## Current Baseline

Source of truth:

- `docs/reports/2026-05-20-north-star-ecosystem-run.md`
- `/tmp/state-system-north-star-ecosystem/north-star-answer.json`

Current result:

```json
{
  "answerability": {
    "status": "usable_with_gaps",
    "source_count": 35,
    "gap_count": 28
  },
  "schema_valid": true
}
```

Current readiness summary:

| Package | Sources | Ready | Usable with gap | Planned | Searchable/access unproven |
|---|---:|---:|---:|---:|---:|
| `instance_agent_package.acme_ops.samantha` | 14 | 12 | 2 | 0 | 0 |
| `instance_agent_package.lfw.caroline` | 7 | 5 | 0 | 2 | 0 |
| `instance_agent_package.navicyte.helena` | 6 | 1 | 0 | 2 | 3 |
| `instance_agent_package.synthyra.ingrid.scaffold.v0` | 8 | 1 | 3 | 1 | 3 |

## Ownership Rules

- Do not touch `.workgraph/graph.jsonl`.
- Do not claim or close unrelated FLIP/evaluator tasks.
- Do not regenerate files in a dirty deployed state root until that lane has captured `git status --short --branch` and claimed its root.
- Do not copy raw source corpora into the product repo or generic examples.
- Prefer `/tmp/...` output during probe/dry-run phases.
- Promote a source only from direct probe evidence. If a source cannot be proven, record a typed failed/planned/unknown state with evidence.

## Shared Variables

Each worker starts with:

```bash
cd /path/to/state-system
export SS=/path/to/state-system
export CHECKED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export STALE_AFTER="$(date -u -v+1H +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p /tmp/state-system-coordination
```

Record the claim:

```bash
{
  echo "## ${USER:-codex} $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  pwd
  git status --short --branch
} >> /tmp/state-system-coordination/claims.md
```

---

### Task 1: Product Surface Stabilization

**Owner:** state-system product agent

**Files:**

- Own existing dirty/untracked product files only:
  - `state_system/north_star_answer.py`
  - `schemas/north-star-answer.schema.json`
  - `tests/test_north_star_answer.py`
  - `state_system/cli.py`
  - `docs/NORTH_STAR.md`
  - `docs/reports/2026-05-20-north-star-ecosystem-run.md`

- [ ] **Step 1: Verify current North Star substrate**

Run:

```bash
cd /path/to/state-system
python3 -m unittest tests.test_north_star_answer
python3 -m unittest tests.test_open_source_ecosystem_conformance
python3 -m state_system.cli --project-root . validate
```

Expected:

- `tests.test_north_star_answer`: 4 tests OK
- `tests.test_open_source_ecosystem_conformance`: 9 tests OK
- `validate`: `ok: true`, `validated_examples: 130`

- [ ] **Step 2: Rerun baseline ecosystem answer**

Run:

```bash
python3 -m state_system.cli --project-root . north-star-answer \
  --query "What is the current cross-instance ecosystem state?" \
  --package bstate=/path/to/personal-state/state/instance-agent-packages/instance_agent_package.acme_ops.samantha.json \
  --package lfw=/path/to/state-system-runtime/state/instance-agent-packages/instance_agent_package.lfw.caroline.json \
  --package navicyte=/path/to/user/projects/work/navicyte/navicyte-workspace/state-system/state/instance-agent-packages/instance_agent_package.navicyte.helena.json \
  --package synthyra=/path/to/user/projects/work/synth/state-system/state/instance-agent-packages/instance_agent_package.synthyra.ingrid.scaffold.v0.json \
  --output-dir /tmp/state-system-north-star-ecosystem
```

Expected:

- exit `0`
- `schema_valid: true`
- current baseline `source_count` and `gap_count` captured before repairs

- [ ] **Step 3: Snapshot the baseline counts**

Run:

```bash
jq '{answerability, gaps: .uncertainty.source_gap_refs, federation: .broader_effects.federated_query_routes}' \
  /tmp/state-system-north-star-ecosystem/north-star-answer.json \
  > /tmp/state-system-coordination/north-star-baseline.json
```

Expected:

- `/tmp/state-system-coordination/north-star-baseline.json` exists
- federation routes have `local_materialization: false`

---

### Task 2: b-state and LFW Source Readiness

**Owner:** personal/LFW operational agent

**Files/Roots:**

- Claim before writing:
  - `/path/to/personal-state`
  - `/path/to/state-system-runtime`

- [ ] **Step 1: Capture dirty status**

Run:

```bash
cd /path/to/personal-state && git status --short --branch
cd /path/to/state-system-runtime && git status --short --branch
```

Expected:

- statuses pasted into `/tmp/state-system-coordination/claims.md`
- no write until root ownership is explicit

- [ ] **Step 2: Refresh existing Beeper adapter**

Run:

```bash
cd /path/to/state-system
STATE_SYSTEM_FLEET_CHECKED_AT="$CHECKED_AT" \
STATE_SYSTEM_FLEET_STALE_AFTER="$STALE_AFTER" \
/path/to/personal-state/fleet-refresh/refresh-beeper-source.sh
```

Expected:

- new or updated records under `/path/to/personal-state/state/instance-preflight-results/`
- new or updated records under `/path/to/personal-state/state/instance-source-freshness/`
- iMessage remains `unknown` unless message-level recency is proven

- [ ] **Step 3: Probe iMessage message-level freshness without reading bodies**

Run:

```bash
export BEEPER_DB="$HOME/Library/Application Support/BeeperTexts/index.db"
sqlite3 "$BEEPER_DB" "PRAGMA table_info(accounts);"
sqlite3 "$BEEPER_DB" "PRAGMA table_info(threads);"
sqlite3 "$BEEPER_DB" "PRAGMA table_info(mx_room_messages);"
sqlite3 "$BEEPER_DB" "SELECT COUNT(*) FROM accounts WHERE platformName='imessage' AND state='enabled';"
sqlite3 "$BEEPER_DB" "SELECT COUNT(*) FROM threads WHERE accountID LIKE 'imessage%' OR thread LIKE '%imessage%';"
```

Expected:

- evidence for either message-level freshness or a truthful no-local-corpus/unknown state
- no message bodies printed or copied

- [ ] **Step 4: Repair Spotify through PAIA source ownership**

Run discovery in PAIA OS:

```bash
cd /path/to/paia-os
rg -n "SPOTIFY_CLIENT|spotify_auth_url|spotify_callback|SpotifySyncService" src scripts tests
```

Expected:

- identify OAuth/sync path
- do not record Spotify `fresh` in State System until live API sync or source-owned freshness evidence exists

- [ ] **Step 5: Prove raw LFW transcript path and inventory**

Run:

```bash
export TRANSCRIPT_ROOT=/path/to/acme-operations/transcripts
test -d "$TRANSCRIPT_ROOT"
find "$TRANSCRIPT_ROOT" -type f \( -name '*.vtt' -o -name '*.md' -o -name '*.txt' \) -print | wc -l
find "$TRANSCRIPT_ROOT" -type f \( -name '*.vtt' -o -name '*.md' -o -name '*.txt' \) -print0 | xargs -0 stat -f '%m %N' | sort -nr | head -1
```

Expected:

- path exists and count is nonzero before `access_status=passed`
- raw transcript bodies remain source-owned

- [ ] **Step 6: Build LFW transcript indexes before promotion**

Create source-owned artifacts in the LFW state root only after root ownership:

- `/path/to/state-system-runtime/transcripts/raw-index/transcript-raw-index.json`
- `/path/to/state-system-runtime/transcripts/processed/transcripts-processed-read-model.json`
- `/path/to/state-system-runtime/transcripts/processed/transcripts-processed-index-manifest.json`

Required artifact policy:

- file refs, mtimes, counts, hashes, safe summaries only
- no raw transcript body copies in State System packages

- [ ] **Step 7: Regenerate b-state and LFW packages**

Run:

```bash
python3 -m state_system.cli --project-root "$SS" \
  --state-root /path/to/personal-state \
  fleet-refresh-run /path/to/personal-state/fleet-refresh/instance-refresh.json \
  --checked-at "$CHECKED_AT" \
  --stale-after "$STALE_AFTER" \
  --output-dir /tmp/state-system-fleet-refresh-bstate

python3 -m state_system.cli --project-root "$SS" \
  --state-root /path/to/state-system-runtime \
  fleet-refresh-run /path/to/state-system-runtime/fleet-refresh/instance-refresh.json \
  --checked-at "$CHECKED_AT" \
  --stale-after "$STALE_AFTER" \
  --output-dir /tmp/state-system-fleet-refresh-lfw
```

Expected:

- updated b-state package: `/path/to/personal-state/state/instance-agent-packages/instance_agent_package.acme_ops.samantha.json`
- updated LFW package: `/path/to/state-system-runtime/state/instance-agent-packages/instance_agent_package.lfw.caroline.json`

---

### Task 3: NaviCyte Source Readiness

**Owner:** NaviCyte operational agent

**Root:**

- `/path/to/user/projects/work/navicyte/navicyte-workspace/state-system`

- [ ] **Step 1: Capture dirty status and baseline**

Run:

```bash
cd /path/to/user/projects/work/navicyte/navicyte-workspace/state-system
git status --short --branch
jq '.source_context.source_readiness[] | {connector_ref, access_status, freshness_status, index_status, understanding_status, gap_refs}' \
  state/instance-agent-packages/instance_agent_package.navicyte.helena.json
```

Expected:

- status and baseline pasted to `/tmp/state-system-coordination/claims.md`

- [ ] **Step 2: Probe Folio, Drive, msgvault, repo, and local index**

Run these probes first; record `passed` or `fresh` only from successful output:

```bash
curl -sS http://localhost:3520/health
curl -sS "http://localhost:3520/api/folio/search?q=Navicyte&tenant_id=navicyte&limit=5" | jq .

/path/to/gws-profiles/bin/gws-account mcco auth status
/path/to/gws-profiles/bin/gws-account mcco drive drives list \
  --params '{"q":"name contains '\''navicyte'\''","pageSize":10}' \
  --format json | jq .

curl -sS http://127.0.0.1:8080/health
msgvault list-accounts --json | jq .
msgvault search "Navicyte" --json --limit 10 | jq .

gh auth status
gh repo view Navicyte/navicyte-workspace --json nameWithOwner,pushedAt,updatedAt,defaultBranchRef,isPrivate
```

Expected:

- each source gets either live evidence or a typed failed/planned explanation

- [ ] **Step 3: Promote only proven NaviCyte sources**

Use `instance-preflight-record` and `instance-source-freshness-record` in this root:

```bash
python3 -m state_system.cli --project-root "$SS" --state-root /path/to/user/projects/work/navicyte/navicyte-workspace/state-system instance-preflight-record --help
python3 -m state_system.cli --project-root "$SS" --state-root /path/to/user/projects/work/navicyte/navicyte-workspace/state-system instance-source-freshness-record --help
```

Expected:

- records created only after probe evidence exists
- unproven sources remain visible as gaps with current evidence

- [ ] **Step 4: Regenerate NaviCyte artifacts**

Run:

```bash
export NAV=/path/to/user/projects/work/navicyte/navicyte-workspace/state-system

python3 -m state_system.cli --project-root "$SS" --state-root "$NAV" instance-preflight-export --output-dir "$NAV/instance-preflight"
python3 -m state_system.cli --project-root "$SS" --state-root "$NAV" instance-source-freshness-export --output-dir "$NAV/instance-source-freshness"
python3 -m state_system.cli --project-root "$SS" --state-root "$NAV" instance-understanding-surface-read --output-dir "$NAV/instance-understanding"
python3 -m state_system.cli --project-root "$SS" --state-root "$NAV" instance-agent-package-build \
  --instance-ref state_instance.navicyte \
  --agent-ref agent.helena \
  --persona-ref persona.helena \
  --package-id instance_agent_package.navicyte.helena \
  --created-at "$CHECKED_AT" \
  --review-goal "Answer Navicyte company-state questions using declared source readiness, explicit freshness evidence, and safe interpreted state."
python3 -m state_system.cli --project-root "$SS" --state-root "$NAV" instance-agent-package-export --output-dir "$NAV/instance-agent-package"
```

Expected:

- Helena package timestamp updates
- gap count drops for proven sources or gaps become explicit real failures

---

### Task 4: Synthyra Source Readiness

**Owner:** Synthyra operational agent

**Root:**

- `/path/to/user/projects/work/synth/state-system`

- [ ] **Step 1: Capture dirty status and baseline**

Run:

```bash
cd /path/to/user/projects/work/synth/state-system
git status --short --branch
jq '.source_context.source_readiness[] | {connector_ref, access_status, freshness_status, index_status, understanding_status, source_watermark, gap_refs}' \
  state/instance-agent-packages/instance_agent_package.synthyra.ingrid.scaffold.v0.json
```

Expected:

- current dirty state and baseline pasted to `/tmp/state-system-coordination/claims.md`

- [ ] **Step 2: Resolve source ownership before promotion**

Run:

```bash
curl -sS http://localhost:3520/health
curl -sS "http://localhost:3520/api/folio/search?q=synthyra&limit=5"

/path/to/gws-profiles/bin/gws-account synthyra auth status
/path/to/gws-profiles/bin/gws-account mcco auth status

/path/to/gws-profiles/bin/gws-account synthyra drive drives list \
  --params '{"q":"name contains '\''Synthyra'\''","pageSize":10}' \
  --format json
/path/to/gws-profiles/bin/gws-account mcco drive drives list \
  --params '{"q":"name contains '\''Synthyra'\''","pageSize":10}' \
  --format json

curl -sS http://127.0.0.1:8080/health
msgvault list-accounts --json
msgvault search "synthyra newer_than:30d" --account user@examplecorp.com --json --limit 5

for repo in Synthyra/atlas Synthyra/synthyra-decks Synthyra/synthyra-ai-org; do
  gh repo view "$repo" --json nameWithOwner,pushedAt,updatedAt,defaultBranchRef,isPrivate
done
```

Expected:

- determine whether Drive should remain `gws:mcco:shared-drive:Synthyra Shared` or move to a `synthyra` profile source ref
- prove source-specific access before changing package readiness

- [ ] **Step 3: Keep transcript docs planned until real pipeline exists**

Do not mark `connector.synthyra.docs.transcripts` fresh until these artifacts exist:

- transcript source location identified
- generated read model with transcript id/title/date/source ref/processed artifact ref/latest processed timestamp
- no raw transcript body copied into package or product repo

Expected:

- transcript gaps remain visible if the pipeline is not built

- [ ] **Step 4: Regenerate Synthyra artifacts**

Run:

```bash
export SYN=/path/to/user/projects/work/synth/state-system

python3 -m state_system.cli --project-root "$SS" --state-root "$SYN" instance-preflight-export --output-dir "$SYN/instance-preflight"
python3 -m state_system.cli --project-root "$SS" --state-root "$SYN" instance-source-freshness-export --output-dir "$SYN/instance-source-freshness"
python3 -m state_system.cli --project-root "$SS" --state-root "$SYN" instance-understanding-surface-read --output-dir "$SYN/instance-understanding"
python3 -m state_system.cli --project-root "$SS" --state-root "$SYN" instance-agent-package-build \
  --instance-ref state_instance.synthyra \
  --agent-ref agent.ingrid \
  --persona-ref persona.ingrid \
  --created-at "$CHECKED_AT" \
  --package-id instance_agent_package.synthyra.ingrid.scaffold.v0 \
  --review-goal "Answer Synthyra company-state questions using declared source readiness, explicit freshness evidence, and safe interpreted state."
python3 -m state_system.cli --project-root "$SS" --state-root "$SYN" instance-agent-package-export --output-dir "$SYN/instance-agent-package"
```

Expected:

- Ingrid package regenerates without hiding failed/planned sources
- repo sources use current GitHub metadata

- [ ] **Step 5: Run Synthyra validator**

Run:

```bash
python3 /path/to/user/projects/work/synth/state-system/tests/validate_synthyra_scaffold.py
```

Expected:

- validator passes or reports only known remaining source-owned gaps

---

### Task 5: North Star Renderer and Render Gate

**Owner:** product renderer agent

**Files:**

- Create: `state_system/north_star_renderer.py`
- Modify: `state_system/cli.py`
- Modify: `tests/test_north_star_answer.py`
- Modify: `docs/NORTH_STAR.md`

- [ ] **Step 1: Write failing renderer tests**

Add tests that require:

- rendered output includes answerability, current state, evidence, uncertainty, responsibility, next actions, broader effects
- every gap ref is visible
- federated route `local_materialization: false` is visible
- non-execution boundary is visible
- render gate fails when the non-execution boundary is removed

Run:

```bash
python3 -m unittest tests.test_north_star_answer
```

Expected before implementation:

- fails because `state_system.north_star_renderer` does not exist

- [ ] **Step 2: Implement `state_system/north_star_renderer.py`**

Public API:

```python
from state_system.stores import JsonObject

def render_north_star_answer_for_agent(answer: JsonObject) -> str:
    lines = ["State System North Star Answer"]
    lines.append(f"Query: {answer['query']}")
    return "\n".join(lines)

def validate_north_star_render(answer: JsonObject, rendered: str) -> list[str]:
    errors: list[str] = []
    if "does not authorize execution" not in rendered:
        errors.append("missing non-execution boundary")
    return errors
```

Required sections:

- `State System North Star Answer`
- `Current state`
- `Why this state`
- `What changed recently`
- `Evidence`
- `Uncertainty`
- `Responsibility`
- `Next actions`
- `Broader effects`
- `Do not`

- [ ] **Step 3: Wire CLI render command**

Add:

```bash
python3 -m state_system.cli --project-root . north-star-answer-render \
  /tmp/state-system-north-star-ecosystem/north-star-answer.json \
  --check \
  --output-path /tmp/state-system-north-star-ecosystem/north-star-answer.txt
```

Expected:

- validates JSON against `schemas/north-star-answer.schema.json`
- validates rendered text with `validate_north_star_render`
- exits `0` and writes a text artifact when both gates pass

- [ ] **Step 4: Validate renderer**

Run:

```bash
python3 -m unittest tests.test_north_star_answer
python3 -m state_system.cli --project-root . north-star-answer-render \
  /tmp/state-system-north-star-ecosystem/north-star-answer.json \
  --check \
  --output-path /tmp/state-system-north-star-ecosystem/north-star-answer.txt
```

Expected:

- tests pass
- rendered text preserves source gaps, evidence refs, freshness boundaries, federation boundaries, and non-execution constraints

---

### Task 6: Ecosystem Aggregation and Final Acceptance

**Owner:** lead coordinator

**Dependencies:**

- Task 1 complete
- Operational instance tasks either complete or explicitly deferred with evidence
- Task 5 renderer complete if product-readable output is in scope for the final check

- [ ] **Step 1: Run ecosystem fleet refresh if instance lanes are ready**

Run only after root ownership is clear:

```bash
python3 -m state_system.cli \
  --project-root /path/to/state-system \
  fleet-refresh-run docs/runbooks/fleet-refresh-acme-ecosystem.json \
  --checked-at "$CHECKED_AT" \
  --stale-after "$STALE_AFTER" \
  --output-dir /tmp/state-system-fleet-refresh-ecosystem
```

Expected:

- top-level `ok` true, or failures limited to documented deferred source-owned repairs
- package-pressure report present when configured by the manifest

- [ ] **Step 2: Rerun North Star ecosystem check**

Run:

```bash
python3 -m state_system.cli --project-root . north-star-answer \
  --query "What is the current cross-instance ecosystem state?" \
  --package bstate=/path/to/personal-state/state/instance-agent-packages/instance_agent_package.acme_ops.samantha.json \
  --package lfw=/path/to/state-system-runtime/state/instance-agent-packages/instance_agent_package.lfw.caroline.json \
  --package navicyte=/path/to/user/projects/work/navicyte/navicyte-workspace/state-system/state/instance-agent-packages/instance_agent_package.navicyte.helena.json \
  --package synthyra=/path/to/user/projects/work/synth/state-system/state/instance-agent-packages/instance_agent_package.synthyra.ingrid.scaffold.v0.json \
  --output-dir /tmp/state-system-north-star-ecosystem
```

Expected:

- exit `0`
- `schema_valid: true`
- `gap_count` decreases, or remaining gaps are documented as real deferred source-owned gaps

- [ ] **Step 3: Inspect final gap movement**

Run:

```bash
jq '.answerability, .uncertainty.source_gap_refs, .next_actions.requires_refresh_before_external_action, .broader_effects.federated_query_routes' \
  /tmp/state-system-north-star-ecosystem/north-star-answer.json
```

Expected:

- federated routes still show `local_materialization: false`
- `requires_refresh_before_external_action` remains true if any material gaps remain

- [ ] **Step 4: Run focused product validation**

Run:

```bash
python3 -m unittest tests.test_north_star_answer
python3 -m unittest tests.test_open_source_ecosystem_conformance
python3 -m state_system.cli --project-root . validate
```

Expected:

- North Star tests pass
- OSS conformance tests pass
- `validate` returns `ok: true`

- [ ] **Step 5: Record final report**

Create a new report:

- `docs/reports/2026-05-20-north-star-gap-closure-status.md`

Required sections:

- source baseline and final counts
- per-instance gap deltas
- sources promoted with evidence
- sources explicitly deferred with reasons
- renderer status if implemented
- exact validation commands and outputs

---

## Final Done Criteria

The ecosystem is "working" for this phase when:

- `north-star-answer` is schema-valid across all four current packages.
- Every source has explicit access/freshness/index/understanding state.
- Any remaining not-ready source is represented as a typed, visible gap.
- Federation routes stay non-materializing.
- A human/agent-readable renderer exists or the renderer task is explicitly next.
- Focused tests and `state_system.cli validate` pass.
- No unrelated FLIP/evaluator or Workgraph claims are made.
