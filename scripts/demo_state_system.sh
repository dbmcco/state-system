#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_ROOT="${STATE_SYSTEM_DEMO_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/state-system-demo.XXXXXX")}"
mkdir -p "$RUN_ROOT"

echo "State System demo"
echo "Project: $ROOT"
echo "Output:  $RUN_ROOT"
echo

echo "==> Run trace manifest"
python3 -m state_system.cli --project-root "$ROOT" \
  trace-run examples/traces/laura-agent-activation.trace.json \
  --output-dir "$RUN_ROOT" > "$RUN_ROOT/trace-run-output.json"

python3 - "$RUN_ROOT/trace-run-output.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"Trace:  {report['trace_id']}")
print(f"Status: {report['status']}")
for step in report["steps"]:
    print(f"    {step['name']}: {step['artifact_path']}")
PY

echo
echo "Demo complete."
echo "Inspect generated artifacts in: $RUN_ROOT"
echo "Report: $RUN_ROOT/index.html"
echo
echo "Rendered activation preview:"
sed -n '1,36p' "$RUN_ROOT/03-rendered-activation.txt"
