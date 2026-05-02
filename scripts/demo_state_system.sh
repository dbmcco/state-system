#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_ROOT="${STATE_SYSTEM_DEMO_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/state-system-demo.XXXXXX")}"
STATE_ROOT="$RUN_ROOT/runtime"
mkdir -p "$STATE_ROOT"

echo "State System demo"
echo "Project: $ROOT"
echo "Runtime: $STATE_ROOT"
echo

run_json() {
  local label="$1"
  local output="$2"
  shift 2
  echo "==> $label"
  "$@" > "$output"
  echo "    wrote $output"
}

echo "==> Seed example state"
python3 - "$ROOT" "$STATE_ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
state_root = Path(sys.argv[2])
objects_dir = state_root / "state" / "objects"
objects_dir.mkdir(parents=True, exist_ok=True)

for name in (
    "southern-abrasives-deal-state.json",
    "lfw-ops-operating-picture.json",
    "marketing-operating-picture.json",
):
    source = root / "examples" / name
    payload = json.loads(source.read_text(encoding="utf-8"))
    target = objects_dir / f"{payload['id']}.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"    seeded {payload['id']}")
PY
echo

cat > "$RUN_ROOT/evidence.json" <<'JSON'
[
  {
    "ref": "linear:deal:southern-abrasives",
    "summary": "Linear deal record for Southern Abrasives.",
    "source_type": "linear_deal",
    "observed_at": "2026-04-28T16:05:00Z"
  },
  {
    "ref": "linear:event:southern-abrasives-stage-won-2026-04-28",
    "summary": "Linear shows Southern Abrasives moved from proposal to won.",
    "source_type": "linear_event",
    "observed_at": "2026-04-28T16:05:00Z"
  }
]
JSON

cat > "$RUN_ROOT/governance.json" <<'JSON'
[
  {
    "id": "governance.external-copy-approval",
    "summary": "External-facing copy requires approval before publication.",
    "approval_required": true
  }
]
JSON

cat > "$RUN_ROOT/routes.json" <<'JSON'
[
  {
    "persona_ref": "persona.patrick",
    "relevance_tier": "primary",
    "routing_reason": "Won deal creates operational handoff.",
    "included": true,
    "opportunity_class_hints": ["operational_handoff"]
  },
  {
    "persona_ref": "persona.laura",
    "relevance_tier": "secondary",
    "routing_reason": "Won deal may become a marketing proof point.",
    "included": true,
    "opportunity_class_hints": ["marketing_opportunity"]
  }
]
JSON

cat > "$RUN_ROOT/sample-agent-response.txt" <<'TEXT'
Draft an internal proof-point note. Hold external publication until public naming and external copy approvals exist.
TEXT

run_json "Validate schemas and examples" "$RUN_ROOT/01-validate.json" \
  python3 -m state_system.cli --project-root "$ROOT" validate

run_json "Ingest source event" "$RUN_ROOT/02-trigger.json" \
  python3 -m state_system.cli --project-root "$ROOT" --state-root "$STATE_ROOT" \
    trigger examples/source-linear-southern-abrasives-won.json

run_json "Build model review packet" "$RUN_ROOT/03-review-packet.json" \
  python3 -m state_system.cli --project-root "$ROOT" --state-root "$STATE_ROOT" \
    review source.linear.southern-abrasives-won \
    --packet-id review_packet.linear.southern-abrasives-won \
    --created-at 2026-04-28T16:05:30Z \
    --persona examples/patrick-persona.json \
    --resolved-evidence "$RUN_ROOT/evidence.json" \
    --governance-constraints "$RUN_ROOT/governance.json" \
    --unresolved-evidence-ref linear:deal:southern-abrasives.public-announcement-permission \
    --unresolved-evidence-ref linear:deal:southern-abrasives.delivery-handoff

run_json "Commit fixture model output" "$RUN_ROOT/04-commit.json" \
  python3 -m state_system.cli --project-root "$ROOT" --state-root "$STATE_ROOT" \
    commit examples/linear-southern-abrasives-won-model-proposal-output.json \
    --created-at 2026-04-28T16:07:00Z \
    --evidence-ref linear:deal:southern-abrasives \
    --evidence-ref linear:event:southern-abrasives-stage-won-2026-04-28

run_json "Read committed state snapshot" "$RUN_ROOT/05-updated-state.json" \
  python3 -m state_system.cli --project-root "$ROOT" --state-root "$STATE_ROOT" \
    get state state.lfw.deal.southern-abrasives

run_json "Index recent change for personas" "$RUN_ROOT/06-recent-change.json" \
  python3 -m state_system.cli --project-root "$ROOT" --state-root "$STATE_ROOT" \
    index-recent source.linear.southern-abrasives-won commit.linear.southern-abrasives-won \
    --created-at 2026-04-28T16:07:30Z \
    --summary "Southern Abrasives moved from proposal to won." \
    --routes "$RUN_ROOT/routes.json" \
    --opportunity-class-hint operational_handoff \
    --opportunity-class-hint marketing_opportunity \
    --watermark-ref state.lfw.deal.southern-abrasives@journal.lfw.deal.southern-abrasives.won \
    --watermark-ref governance.external-copy-approval \
    --stale-after 2026-04-29T16:07:30Z \
    --requires-refresh-before-external-action

run_json "Build Laura context package" "$RUN_ROOT/07-laura-package.json" \
  python3 -m state_system.cli --project-root "$ROOT" --state-root "$STATE_ROOT" \
    build-package examples/laura-persona.json context.laura.demo-recent \
    --created-at 2026-04-28T16:08:00Z \
    --review-goal "Review Laura-relevant recent changes." \
    --valid-until 2026-04-29T16:08:00Z

echo "==> Render package for an agent"
python3 -m state_system.cli --project-root "$ROOT" --state-root "$STATE_ROOT" \
  render-package context.laura.demo-recent > "$RUN_ROOT/08-rendered-package.txt"
echo "    wrote $RUN_ROOT/08-rendered-package.txt"

run_json "Capture sample agent response" "$RUN_ROOT/09-agent-response.json" \
  python3 -m state_system.cli --project-root "$ROOT" --state-root "$STATE_ROOT" \
    capture-response context.laura.demo-recent "$RUN_ROOT/sample-agent-response.txt" \
    --consumer consumer.demo \
    --created-at 2026-04-28T16:09:00Z

echo
echo "Demo complete."
echo "Inspect generated artifacts in: $RUN_ROOT"
echo
echo "Rendered package preview:"
sed -n '1,32p' "$RUN_ROOT/08-rendered-package.txt"
