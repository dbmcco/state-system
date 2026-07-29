# Deployed state-root rollout plan

**Discovery timestamp:** 2026-07-29 UTC
**Scope:** read-only inspection only. No deployed root, private corpus, credential,
or generated runtime artifact was modified or copied into this product worktree.

## Preconditions and rollout gate

Product checks were freshly run in this worktree before inspecting any deployed
root:

```bash
python3 -m unittest discover -s tests
python3 -m state_system.cli --project-root . validate
```

They exited `0`; validation reported `ok: true`, `validated_examples: 149`.

The evidence-grounding blocker documented in
`.workgraph/reviews/content-accuracy-adversarial.md` remains open:
`product.fix.commit-evidence-grounding`. It is a **mutation gate**. This plan
supports discovery and a future dry-run, but no root may be refreshed until that
blocker is fixed or an explicit replan supersedes it. The existing
`deployed.rollout.roots` task remains paused.

`validate-runtime` does **not** exist in `python3 -m state_system.cli --help`.
The supported fallback form exists and was read-only tested against every root:

```bash
python3 -m state_system.cli --project-root . --state-root "$ROOT" validate
```

It exited `0` for all four roots and reported the product's 149 validated
examples. It is a product-contract check, not a claim that private runtime data
is healthy; the rendered report/package checks below remain required.

## Exact roots inspected

| Instance | Exact state root inspected | Root status | Refresh-path decision |
| --- | --- | --- | --- |
| LFW | `/Users/braydon/projects/work/lfw/state-system` | Exists; readable and writable; not a Git repository | Existing root manifest is the refresh path. |
| Synthyra | `/Users/braydon/projects/work/synth/state-system` | Exists; readable and writable; not a Git repository | Existing root manifest is the refresh path. |
| b-state | `/Users/braydon/projects/personal/b-state` | Exists; readable and writable; not a Git repository | Existing root manifest, including ECS wiring, is the refresh path. |
| Navicyte | `/Users/braydon/projects/work/navicyte/navicyte-workspace/state-system` | Exists; readable and writable; not a Git repository | **Confirmed refresh path.** The shorthand `/Users/braydon/projects/work/navicyte` is a workspace; this nested root is the deployed State System root. No escalation is needed for a missing Navicyte root. |

All four roots have `fleet-refresh/instance-refresh.json`, one configured
instance, and declared adapter-command wiring. The manifest shape is compatible
with the current runner (`default_ttl_seconds`, `description`, `id`, and
`instances`; b-state additionally has `entity_current_state`). No structural
manifest migration was discovered. Do not infer that an adapter is healthy from
that structural compatibility.

## Audited surfaces and ages

Ages below are approximate filesystem ages at discovery on 2026-07-29 UTC.
Exact report timestamps are included where present. `ok: false` is a visible
operational gap, not a reason to write a healthy surface.

| Root | Inspected generated/report paths and current age | Current report / surface observation |
| --- | --- | --- |
| LFW | `instance-agent-package/instance-agent-packages-read-model.json` ~0.1h; `strategic-staleness/strategic-staleness-read-model.json` ~0.1h; `fleet-refresh/fleet-refresh-report.json` ~0.1h; `company-understanding/company-understanding-surface-read-model.json` ~897.4h (~37.4d); manifest ~1321.2h (~55.0d). | Fleet report: `checked_at=2026-07-29T21:33:07Z`, `stale_after=2026-07-29T22:33:07Z`, `ok=false`. Strategic status: `no_reviewable_findings`. Company understanding is materially older than the fleet outputs. |
| Synthyra | `instance-agent-package/instance-agent-packages-read-model.json` ~0.1h; `strategic-staleness/strategic-staleness-read-model.json` ~0.1h; `fleet-refresh/fleet-refresh-report.json` ~0.1h; `company-understanding/company-understanding-surface-read-model.json` ~1328.4h (~55.4d); manifest ~1321.4h (~55.1d). | Fleet report: `checked_at=2026-07-29T21:32:30Z`, `stale_after=2026-07-29T22:32:30Z`, `ok=false`. Strategic status: `no_reviewable_findings`. Company understanding is materially older than the fleet outputs. |
| b-state | `instance-agent-package/instance-agent-packages-read-model.json` ~0.6h; `strategic-staleness/strategic-staleness-read-model.json` ~0.6h; `fleet-refresh/fleet-refresh-report.json` ~0.6h; root-level `fleet-refresh-report.json` ~292.5h (~12.2d); manifest ~24.0h. No company-understanding surface was present. | Fleet report: `checked_at=2026-07-29T21:03:17Z`, `stale_after=2026-07-29T22:03:17Z`, `ok=false`. Strategic status: `awaiting_model_review`, which is an explicit gap rather than a healthy claim. |
| Navicyte | `instance-agent-package/instance-agent-packages-read-model.json` ~0.1h; `strategic-staleness/strategic-staleness-read-model.json` ~0.1h; `fleet-refresh/fleet-refresh-report.json` ~0.1h; manifest ~1321.4h (~55.1d). No company-understanding surface was present. | Fleet report: `checked_at=2026-07-29T21:32:49Z`, `stale_after=2026-07-29T22:32:49Z`, `ok=false`. Strategic status: `no_reviewable_findings`. |

The root-level b-state `fleet-refresh-report.json` is an older duplicate-style
surface. Treat the current `fleet-refresh/fleet-refresh-report.json` as the
active report unless the rollout owner explicitly changes routing; do not delete
the older file during this rollout.

## Current readiness and required updates

The following counts select only the newest record for each connector/source
key. Historical append-only records were not treated as current health.

| Root | Latest source-freshness state | Latest preflight state | Required rollout work |
| --- | --- | --- | --- |
| LFW | 26 records: 11 fresh, 4 stale, 8 unknown, 2 failed, 1 missing; 23 have expired `stale_after`. | 25 records: 20 passed, 3 failed, 1 planned, 1 missing; 23 expired. | **Data/operational refresh required.** Diagnose failed/unknown/stale sources through declared adapters, then regenerate package, understanding, and strategic surfaces. Rebuild the old company-understanding surface. No manifest schema change is indicated before dry-run evidence. |
| Synthyra | 19 records: 3 fresh, 5 stale, 10 unknown, 1 missing; 15 expired. | 16 records: 9 passed, 6 failed, 1 missing; 13 expired. | **Data/operational refresh required.** Resolve adapter/preflight gaps before accepting any report as healthy; regenerate package, understanding, and strategic surfaces. Rebuild the old company-understanding surface. No manifest schema change is indicated before dry-run evidence. |
| b-state | 21 records: 11 fresh, 5 stale, 4 unknown, 1 missing; 8 expired. | 15 records: 14 passed, 1 missing; 10 expired. | **Data refresh and model-review follow-up required.** Keep the explicit `awaiting_model_review` state until an authorized reviewer supplies judgment. Its ECS manifest wiring is present; do not add a company surface unless an operator decides that this personal instance needs company scope. |
| Navicyte | 7 records: 3 fresh, 1 stale, 2 unknown, 1 missing; 2 expired. | 7 records: 6 passed, 1 missing; 4 expired. | **Data/operational refresh required.** Use the confirmed nested root and existing manifest. The path/config decision is refresh, not satellite removal. Do not add a company surface without a business decision. |

A failed or unknown adapter must remain a report/package gap after refresh. Do
not change manifest status or render a healthy report merely to make `ok` true.
If a dry-run reveals an adapter command, output directory, or package route that
is incompatible with the current runner, create a bounded config-migration
follow-up rather than editing private runtime structure ad hoc.

## Future rollout sequence (after the blocker is resolved)

Run from the approved checkout of this product repository. For each exact root,
set `ROOT` to the value in the table above and use its existing manifest:

```bash
ROOT=/Users/braydon/projects/work/lfw/state-system  # substitute exact target
MANIFEST="$ROOT/fleet-refresh/instance-refresh.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$ROOT/rollout-backups/$STAMP"

# 1. Preserve only replaceable generated surfaces locally in the private root.
#    Do not copy raw indexes, credentials, or state history into this repo.
mkdir -p "$BACKUP_DIR"
for path in \
  fleet-refresh/fleet-refresh-report.json \
  instance-agent-package/instance-agent-packages-read-model.json \
  strategic-staleness/strategic-staleness-read-model.json \
  company-understanding/company-understanding-surface-read-model.json
do
  test -e "$ROOT/$path" && cp -p "$ROOT/$path" "$BACKUP_DIR/$(basename "$path")"
done

# 2. Preview the exact declared adapters before writes. This must show gaps,
#    not be treated as approval to bypass them.
python3 -m state_system.cli --project-root . --state-root "$ROOT" \
  fleet-refresh-run "$MANIFEST" --reviewer none \
  --output-dir "$ROOT/fleet-refresh" --dry-run

# 3. Only after owner approval of the preview, run the declared refresh.
python3 -m state_system.cli --project-root . --state-root "$ROOT" \
  fleet-refresh-run "$MANIFEST" --reviewer none \
  --output-dir "$ROOT/fleet-refresh"
```

`--reviewer none` is deliberate: it preserves explicit
`awaiting_model_review` gaps rather than fabricating strategic judgment. A live
reviewer requires an injected model client; the CLI rejects unsupported
`--reviewer live` use. Use `--reviewer recorded` only when the rollout owner has
identified an appropriate recorded-review input for that root.

Run the sequence separately for:

```text
/Users/braydon/projects/work/lfw/state-system
/Users/braydon/projects/work/synth/state-system
/Users/braydon/projects/personal/b-state
/Users/braydon/projects/work/navicyte/navicyte-workspace/state-system
```

## Verification and rollback

For every root, run the available CLI verification form before and after the
refresh:

```bash
python3 -m state_system.cli --project-root . --state-root "$ROOT" validate
```

Then inspect these root-local outputs without copying their contents into the
product repository:

```bash
test -s "$ROOT/fleet-refresh/fleet-refresh-report.json"
test -s "$ROOT/instance-agent-package/instance-agent-packages-read-model.json"
test -s "$ROOT/strategic-staleness/strategic-staleness-read-model.json"
python3 - <<'PY' "$ROOT/fleet-refresh/fleet-refresh-report.json"
import json, sys
report = json.load(open(sys.argv[1]))
print({key: report.get(key) for key in ("checked_at", "stale_after", "ok")})
PY
```

For LFW and Synthyra also verify a regenerated
`company-understanding/company-understanding-surface-read-model.json`; for
b-state and Navicyte, preserve the observed absence unless a separate scope
explicitly adds company-level coverage. Evaluate report/package gaps and
strategic-review status as operational evidence; a report remains unacceptable
if it hides stale, failed, unknown, missing, or `awaiting_model_review` states.

Rollback is limited to restoring the local backup copies of named rendered
surfaces. Do **not** delete append-only freshness/preflight/history records to
simulate rollback. If an adapter refresh produces an incorrect record, use a
forward corrective record and retain audit history. Restore only after stopping
the scheduled refresh for that root and recording the reason in Workgraph.

## Discovery-only record

This node made no live-root mutation. Its only artifact is this plan. The
initial drift invocation required explicit `--dir .workgraph` because this
worktree contains both `.workgraph` and `.wg`; that local control-plane issue is
separate from all deployed roots and is recorded in the task log.
