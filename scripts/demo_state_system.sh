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

echo "==> Run report suite"
python3 -m state_system.cli --project-root "$ROOT" \
  report-suite-run \
  --output-dir "$RUN_ROOT" > "$RUN_ROOT/report-suite-output.json"

python3 - "$RUN_ROOT/report-suite-output.json" <<'PY'
import json
import sys
from pathlib import Path

suite = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"Suite:  {suite['id']}")
print(f"Status: {suite['status']}")
for report in suite["reports"]:
    print(f"    {report['title']}: {report['report_path']}")
PY

echo
echo "Demo complete."
echo "Inspect generated artifacts in: $RUN_ROOT"
echo "Report Suite: $RUN_ROOT/index.html"
echo
echo "Mission report preview:"
sed -n '1,36p' "$RUN_ROOT/mission-records/index.html"
