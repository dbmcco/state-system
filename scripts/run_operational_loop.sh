#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_ROOT="${STATE_SYSTEM_OPERATIONAL_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/state-system-operational.XXXXXX")}"
mkdir -p "$RUN_ROOT"

python3 -m state_system.cli --project-root "$ROOT" \
  operational-loop-run \
  examples/operational-loop/southern-abrasives-loop.trace.json \
  --output-dir "$RUN_ROOT" > "$RUN_ROOT/operational-loop-output.json"

python3 - "$RUN_ROOT/operator-summary.json" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"Operational loop: {summary['id']}")
print(f"Status: {summary['status']}")
print(f"Source event: {summary['source']['source_event_id']}")
print(f"Commit: {summary['commit']['id']} ({summary['commit']['status']})")
print(f"Accepted state: {', '.join(summary['accepted_state_refs'])}")
print(f"Context package: {summary['working_model']['context_package_id']}")
print(f"Activation: {summary['agent']['activation_id']}")
print(f"Response: {summary['agent']['response_id']}")
print(f"Response becomes truth: {summary['agent']['response_becomes_truth']}")
PY

echo
echo "Output: $RUN_ROOT"
echo "Operator summary: $RUN_ROOT/operator-summary.json"
echo "Trace report: $RUN_ROOT/trace/index.html"
