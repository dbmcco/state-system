#!/bin/sh
# ABOUTME: per-root cron loop for canonical-claim edit detection + live reconcile.
# ABOUTME: scans the canonical-claims store for human edits, then reconciles any
# ABOUTME: unreconciled edits through the live (model-mediated) reviewer.
# usage: run-canon-reconcile.sh STATE_ROOT
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: run-canon-reconcile.sh STATE_ROOT" >&2
  exit 64
fi

PROJECT_ROOT="/Users/braydon/projects/experiments/state-system"
STATE_ROOT="$1"
BASELINE="${STATE_ROOT}/state/canon-edit-baseline.json"
LOG_DIR="${STATE_ROOT}/canon-reconcile"
LOCK_DIR="${LOG_DIR}/.canon-reconcile.lock"
MODEL_ROUTE="${STATE_SYSTEM_CANON_MODEL:-zai/glm-5.2}"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export PATH="/Users/braydon/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH}"

mkdir -p "$LOG_DIR"
# Per-root lock so overlapping cron cycles do not double-reconcile.
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  lock_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  lock_cmd="$(ps -p "$lock_pid" -o command= 2>/dev/null || true)"
  case "$lock_cmd" in
    *run-canon-reconcile.sh*"$STATE_ROOT"*)
      echo "canon-reconcile already running for ${STATE_ROOT}" >&2
      exit 0
      ;;
    *)
      rm -f "$LOCK_DIR/pid"; rmdir "$LOCK_DIR" 2>/dev/null || true
      mkdir "$LOCK_DIR" 2>/dev/null || { echo "canon-reconcile lock busy" >&2; exit 0; }
      ;;
  esac
fi
printf '%s\n' "$$" > "$LOCK_DIR/pid"
trap 'rm -f "$LOCK_DIR/pid"; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT INT TERM

# 1. Detect raw human edits (adds/edits/deletes) since the last baseline.
SCAN_JSON="$(uv run --project "$PROJECT_ROOT" --with jsonschema python -m state_system.cli \
  --project-root "$PROJECT_ROOT" --state-root "$STATE_ROOT" \
  canon-edit-scan --baseline-path "$BASELINE" --detected-at "$NOW")"
EMITTED="$(printf '%s' "$SCAN_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("emitted_count",0))')"

# 2. Reconcile any unreconciled edits through the live model-mediated reviewer.
#    Only runs when there is something to reconcile (avoids needless model cost).
RECONCILE_JSON='{"ok":true,"reviewed_count":0,"skipped":true}'
if [ "${EMITTED}" -gt 0 ] || ls "${STATE_ROOT}/state/canon-edits"/*.json >/dev/null 2>&1; then
  RECONCILE_JSON="$(uv run --project "$PROJECT_ROOT" --with jsonschema python -m state_system.cli \
    --project-root "$PROJECT_ROOT" --state-root "$STATE_ROOT" \
    canon-edit-reconcile-run --as-of "$NOW" --reviewer live --model "$MODEL_ROUTE" 2>&1 || true)"
fi

printf '%s\n' "$RECONCILE_JSON" > "${LOG_DIR}/canon-reconcile-report.json"
python3 -c "
import json, sys
scan = json.loads('''$SCAN_JSON''')
try: rec = json.loads(sys.argv[1])
except Exception: rec = {'raw': sys.argv[1][:300]}
print(json.dumps({'checked_at': '$NOW', 'state_root': '$STATE_ROOT',
  'emitted': scan.get('emitted_count', 0), 'reviewed': rec.get('reviewed_count', 'n/a'),
  'ok': rec.get('ok', 'n/a')}, indent=2))
" "$RECONCILE_JSON" > "${LOG_DIR}/status.json"
cat "${LOG_DIR}/status.json"
