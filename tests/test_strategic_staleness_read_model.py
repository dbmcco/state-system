from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.staleness_runner import parse_instant
from state_system.strategic_staleness import refresh_strategic_staleness_read_model


AS_OF = parse_instant("2026-06-25T12:00:00Z")


def _entity_current_state(entity_id: str = "venture.cyrcle") -> dict:
    return {
        "id": f"entity_current_state.{entity_id}.2026-06-18T13-14-00Z",
        "entity_id": entity_id,
        "entity_name": entity_id,
        "north_star": "Ship the current-state app before the Friday review.",
        "current_priority": "Background agent progress needs verification.",
        "owner": "Braydon",
        "waiting_on": "agent progress",
        "braydon_next_action": "verify agent progress",
        "effective_at": "2026-06-18T13:14:00Z",
        "stale_after": "2026-06-20T12:00:00Z",
        "supersedes": None,
        "source_refs": ["folio:ecs-note", "workboard:ecs-task"],
        "confidence": "high",
        "status": "active",
        "generated_at": "2026-06-18T13:14:00Z",
        "generated_by": "sam",
    }


class StrategicStalenessReadModelShellTests(unittest.TestCase):
    def test_unreviewed_expired_ecs_card_is_visible_as_awaiting_review_not_empty(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            ecs_dir = state_root / "state" / "entity-current-state"
            ecs_dir.mkdir(parents=True)
            ecs_dir.joinpath(
                "entity_current_state.venture.cyrcle.2026-06-18T13-14-00Z.json"
            ).write_text(json.dumps(_entity_current_state()), encoding="utf-8")

            out_path = refresh_strategic_staleness_read_model(
                state_root,
                as_of=AS_OF,
                reviewer=None,
            )
            read_model = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertIn("venture.cyrcle", read_model["latest_by_entity_id"])
        judgment = read_model["latest_by_entity_id"]["venture.cyrcle"]
        self.assertEqual("awaiting_model_review", judgment["review_status"])
        self.assertEqual("entity_current_state", judgment["claim_kind"])
        self.assertTrue(judgment["validity_window_exceeded"])
        self.assertIn("folio:ecs-note", judgment["evidence_refs"])
        self.assertIn("nl_question", judgment)


if __name__ == "__main__":
    unittest.main()
