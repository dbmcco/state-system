from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_validate_runs_without_model_or_runtime_state(self):
        output = StringIO()

        code = cli.main(["--project-root", str(ROOT), "validate"], stdout=output)

        payload = json.loads(output.getvalue())
        self.assertEqual(0, code)
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["validated_examples"], 0)

    def test_trigger_ingests_source_event_and_prints_trigger(self):
        with TemporaryDirectory() as directory:
            source_path = ROOT / "examples" / "source-linear-southern-abrasives-won.json"
            output = StringIO()

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "trigger",
                    str(source_path),
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["created"])
            self.assertEqual("trigger.linear.southern-abrasives-won", payload["trigger"]["id"])
            stores = StateStoreBundle(Path(directory))
            self.assertEqual(
                ["source.linear.southern-abrasives-won"],
                stores.source_events.list_ids(),
            )

    def test_get_memory_recent_package_and_rollups_are_machine_readable(self):
        with TemporaryDirectory() as directory:
            stores = self._seed_runtime(Path(directory))

            get_output = StringIO()
            get_code = cli.main(
                [
                    "--state-root",
                    directory,
                    "get",
                    "state",
                    "state.lfw.deal.southern-abrasives",
                ],
                stdout=get_output,
            )
            self.assertEqual(0, get_code)
            self.assertEqual(
                "state.lfw.deal.southern-abrasives",
                json.loads(get_output.getvalue())["id"],
            )

            memory_output = StringIO()
            memory_code = cli.main(
                ["--state-root", directory, "memory", "persona.laura"],
                stdout=memory_output,
            )
            self.assertEqual(0, memory_code)
            self.assertEqual(
                ["memory.laura.marketing.draft.audience-before-copy"],
                [entry["id"] for entry in json.loads(memory_output.getvalue())["entries"]],
            )

            recent_output = StringIO()
            recent_code = cli.main(
                ["--state-root", directory, "recent", "persona.laura"],
                stdout=recent_output,
            )
            self.assertEqual(0, recent_code)
            self.assertEqual(
                ["recent.linear.southern-abrasives-won"],
                [entry["id"] for entry in json.loads(recent_output.getvalue())["entries"]],
            )

            package_output = StringIO()
            package_code = cli.main(
                [
                    "--state-root",
                    directory,
                    "package",
                    "context.laura.southern-abrasives-won-opportunity",
                ],
                stdout=package_output,
            )
            self.assertEqual(0, package_code)
            self.assertEqual(
                "context.laura.southern-abrasives-won-opportunity",
                json.loads(package_output.getvalue())["id"],
            )

            rollups_output = StringIO()
            rollups_code = cli.main(
                ["--state-root", directory, "rollups"],
                stdout=rollups_output,
            )
            self.assertEqual(0, rollups_code)
            self.assertEqual(
                ["state.operating_picture.marketing"],
                [
                    item["state_object_id"]
                    for item in json.loads(rollups_output.getvalue())["rollup_requests"]
                    if item["state_object_id"] == "state.operating_picture.marketing"
                ],
            )
            self.assertIn("recent.linear.southern-abrasives-won", stores.recent_changes.list_ids())

    def _seed_runtime(self, root: Path) -> StateStoreBundle:
        stores = StateStoreBundle(root)
        stores.state_objects.create(
            load_json(ROOT / "examples" / "southern-abrasives-deal-state-after-won.json")
        )
        stores.memory.create(load_json(ROOT / "examples" / "laura-agent-memory-entry.json"))
        stores.recent_changes.create(
            load_json(ROOT / "examples" / "recent-linear-southern-abrasives-won.json")
        )
        stores.context_packages.create(
            load_json(
                ROOT / "examples" / "laura-southern-abrasives-opportunity-context-package.json"
            )
        )
        stores.commits.create(
            load_json(ROOT / "examples" / "linear-southern-abrasives-won-commit-result.json")
        )
        return stores


if __name__ == "__main__":
    unittest.main()
