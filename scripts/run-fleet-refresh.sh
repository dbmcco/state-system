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

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "fleet refresh already running for ${MANIFEST}" >&2
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT INT TERM

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

python3 -m state_system.cli \
  --project-root "$PROJECT_ROOT" \
  fleet-refresh-run "$MANIFEST" \
  --output-dir "$OUTPUT_DIR"
