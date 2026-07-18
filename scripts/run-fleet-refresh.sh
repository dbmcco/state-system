#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: run-fleet-refresh.sh MANIFEST OUTPUT_DIR" >&2
  exit 64
fi

PROJECT_ROOT="/Users/braydon/projects/experiments/state-system"
MANIFEST="$1"
OUTPUT_DIR="$2"
LOCK_DIR="${OUTPUT_DIR}/.fleet-refresh.lock"
LOCK_PID_FILE="${LOCK_DIR}/pid"
# All instances share this lock because their metadata adapters may query MsgVault.
GLOBAL_LOCK_DIR="${STATE_SYSTEM_GLOBAL_FLEET_LOCK_DIR:-/Users/braydon/projects/personal/b-state/fleet-refresh/.state-system-fleet-refresh.lock}"
GLOBAL_LOCK_PID_FILE="${GLOBAL_LOCK_DIR}/pid"
GLOBAL_LOCK_ACQUIRED=0

mkdir -p "$OUTPUT_DIR" "$(dirname "$GLOBAL_LOCK_DIR")"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  lock_pid="$(cat "$LOCK_PID_FILE" 2>/dev/null || true)"
  lock_command=""
  if [ -n "$lock_pid" ]; then
    lock_command="$(ps -p "$lock_pid" -o command= 2>/dev/null || true)"
  fi
  case "$lock_command" in
    *run-fleet-refresh.sh*"$MANIFEST"*"$OUTPUT_DIR"*)
      echo "fleet refresh already running for ${MANIFEST}" >&2
      exit 0
      ;;
    *)
      rm -f "$LOCK_PID_FILE"
      rmdir "$LOCK_DIR" 2>/dev/null || true
      if ! mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "fleet refresh already running for ${MANIFEST}" >&2
        exit 0
      fi
      ;;
  esac
fi
printf '%s\n' "$$" > "$LOCK_PID_FILE"
cleanup_lock() {
  rm -f "$LOCK_PID_FILE"
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
acquire_global_lock() {
  global_waited=0
  while ! mkdir "$GLOBAL_LOCK_DIR" 2>/dev/null; do
    global_pid="$(cat "$GLOBAL_LOCK_PID_FILE" 2>/dev/null || true)"
    global_command=""
    if [ -n "$global_pid" ]; then
      global_command="$(ps -p "$global_pid" -o command= 2>/dev/null || true)"
    fi
    case "$global_command" in
      *run-fleet-refresh.sh*)
        ;;
      *)
        rm -f "$GLOBAL_LOCK_PID_FILE"
        rmdir "$GLOBAL_LOCK_DIR" 2>/dev/null || true
        continue
        ;;
    esac
    if [ "$global_waited" -ge "${STATE_SYSTEM_GLOBAL_FLEET_WAIT_SECONDS:-1800}" ]; then
      echo "state system global fleet lock wait exceeded" >&2
      exit 75
    fi
    sleep 15
    global_waited=$((global_waited + 15))
  done
  printf '%s\n' "$$" > "$GLOBAL_LOCK_PID_FILE"
  GLOBAL_LOCK_ACQUIRED=1
}
cleanup_global_lock() {
  if [ "$GLOBAL_LOCK_ACQUIRED" -eq 1 ] && [ "$(cat "$GLOBAL_LOCK_PID_FILE" 2>/dev/null || true)" = "$$" ]; then
    rm -f "$GLOBAL_LOCK_PID_FILE"
    rmdir "$GLOBAL_LOCK_DIR" 2>/dev/null || true
  fi
}
trap 'cleanup_lock; cleanup_global_lock' EXIT INT TERM

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export PATH="/Users/braydon/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

RELATIONSHIP_LOCK_DIR="${RELATIONSHIP_SUBSTRATE_COORDINATION_LOCK_DIR:-/Users/braydon/projects/personal/b-state/fleet-refresh/.relationship-substrate-cycle.lock}"
RELATIONSHIP_WAIT_SECONDS="${STATE_SYSTEM_RELATIONSHIP_WAIT_SECONDS:-1800}"
relationship_waited=0
while [ -d "$RELATIONSHIP_LOCK_DIR" ]; do
  relationship_pid="$(cat "$RELATIONSHIP_LOCK_DIR/pid" 2>/dev/null || true)"
  relationship_command=""
  if [ -n "$relationship_pid" ]; then
    relationship_command="$(ps -p "$relationship_pid" -o command= 2>/dev/null || true)"
  fi
  case "$relationship_command" in
    *substrate-cycle.sh*)
      ;;
    "")
      if [ "$relationship_waited" -eq 0 ]; then
        sleep 1
        relationship_waited=1
        continue
      fi
      rm -f "$RELATIONSHIP_LOCK_DIR/pid"
      rmdir "$RELATIONSHIP_LOCK_DIR" 2>/dev/null || true
      continue
      ;;
    *)
      rm -f "$RELATIONSHIP_LOCK_DIR/pid"
      rmdir "$RELATIONSHIP_LOCK_DIR" 2>/dev/null || true
      continue
      ;;
  esac
  if [ "$relationship_waited" -ge "$RELATIONSHIP_WAIT_SECONDS" ]; then
    echo "relationship substrate coordination wait exceeded ${RELATIONSHIP_WAIT_SECONDS}s" >&2
    exit 75
  fi
  sleep 15
  relationship_waited=$((relationship_waited + 15))
done

acquire_global_lock
uv run --project "$PROJECT_ROOT" --with jsonschema python -m state_system.cli \
  --project-root "$PROJECT_ROOT" \
  fleet-refresh-run "$MANIFEST" \
  --output-dir "$OUTPUT_DIR"
