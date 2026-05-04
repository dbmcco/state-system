from pathlib import Path
from io import StringIO
import json
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.mission_records import (
    MissionStoreBundle,
    build_mission_read_model,
    replay_mission_fixture,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "missions" / "repo-audit-streamlinear.json"


class MissionReplayTests(unittest.TestCase):
    def test_replay_is_idempotent_and_creates_expected_records(self):
        with TemporaryDirectory() as directory:
            stores = MissionStoreBundle(Path(directory))

            first = replay_mission_fixture(FIXTURE, stores)
            second = replay_mission_fixture(FIXTURE, stores)

            self.assertEqual("mission.repo_audit.streamlinear", first["mission_run_id"])
            self.assertEqual(1, first["created"]["mission_runs"])
            self.assertEqual(0, second["created"]["mission_runs"])
            self.assertEqual(6, len(stores.agent_runs.replay()))
            self.assertGreaterEqual(len(stores.events.replay()), 8)
            self.assertEqual(2, len(stores.findings.replay()))
            self.assertEqual(1, len(stores.stumbles.replay()))
            self.assertEqual(1, len(stores.governance_receipts.replay()))
            self.assertEqual(1, len(stores.commit_results.replay()))
            self.assertEqual(1, len(stores.journal_entries.replay()))
            self.assertEqual(1, len(stores.memory_entries.replay()))
            self.assertEqual(1, len(stores.review_signals.replay()))

    def test_read_model_regenerates_from_records(self):
        with TemporaryDirectory() as directory:
            stores = MissionStoreBundle(Path(directory))
            replay_mission_fixture(FIXTURE, stores)

            read_model = build_mission_read_model(
                stores,
                "mission.repo_audit.streamlinear",
            )

            self.assertEqual("mission.repo_audit.streamlinear", read_model["mission"]["id"])
            self.assertEqual("completed", read_model["mission"]["status"])
            self.assertEqual(6, len(read_model["agent_roster"]))
            self.assertGreaterEqual(len(read_model["timeline"]), 8)
            self.assertEqual(
                {"security_risk", "missing_evidence"},
                {finding["finding_type"] for finding in read_model["findings"]},
            )
            self.assertEqual("blocked_by_policy", read_model["governance"][0]["status"])
            self.assertIn("wg:task:streamlinear-security-hardening", read_model["follow_ups"])

    def test_cli_replays_fixture_and_writes_read_model(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "mission-replay",
                    str(FIXTURE),
                    "--output-dir",
                    directory,
                ],
                stdout=output,
            )

            self.assertEqual(0, code)
            payload = json.loads(output.getvalue())
            self.assertEqual("mission.repo_audit.streamlinear", payload["mission_run_id"])
            read_model_path = Path(payload["read_model_path"])
            self.assertTrue(read_model_path.exists())
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual("completed", read_model["mission"]["status"])


if __name__ == "__main__":
    unittest.main()
