from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.stores import (
    DEFAULT_COLLECTIONS,
    JsonFileStore,
    RecordExistsError,
    RecordNotFoundError,
    StateStoreBundle,
)


class JsonFileStoreTests(unittest.TestCase):
    def test_create_and_read_record_from_runtime_state_directory(self):
        with TemporaryDirectory() as directory:
            store = JsonFileStore(Path(directory), "objects")
            record = {
                "id": "state.example",
                "created_at": "2026-04-29T12:00:00Z",
                "summary": "Example state.",
            }

            written_path = store.create(record)

            self.assertEqual(
                Path(directory) / "state" / "objects" / "state.example.json",
                written_path,
            )
            self.assertEqual(record, store.read("state.example"))
            self.assertFalse((Path(directory) / "examples").exists())

    def test_missing_record_raises_not_found(self):
        with TemporaryDirectory() as directory:
            store = JsonFileStore(Path(directory), "journals")

            with self.assertRaises(RecordNotFoundError):
                store.read("journal.missing")

    def test_duplicate_record_id_is_rejected(self):
        with TemporaryDirectory() as directory:
            store = JsonFileStore(Path(directory), "source-events")
            record = {
                "id": "source.linear.example",
                "observed_at": "2026-04-29T12:00:00Z",
            }

            store.create(record)

            with self.assertRaises(RecordExistsError):
                store.create(record)

    def test_replay_is_deterministic_by_record_time_then_id(self):
        with TemporaryDirectory() as directory:
            store = JsonFileStore(Path(directory), "memory")
            store.create({"id": "memory.c", "created_at": "2026-04-29T12:02:00Z"})
            store.create({"id": "memory.b", "created_at": "2026-04-29T12:01:00Z"})
            store.create({"id": "memory.a", "created_at": "2026-04-29T12:01:00Z"})

            self.assertEqual(
                ["memory.a", "memory.b", "memory.c"],
                [record["id"] for record in store.replay()],
            )

    def test_default_bundle_exposes_generic_state_collections(self):
        with TemporaryDirectory() as directory:
            bundle = StateStoreBundle(Path(directory))

            self.assertEqual(
                {
                    "state_objects",
                    "source_events",
                    "review_packets",
                    "journals",
                    "memory",
                    "rollups",
                    "review_signals",
                    "commits",
                    "recent_changes",
                    "context_packages",
                    "agent_activations",
                    "agent_responses",
                    "instance_capabilities",
                    "instance_preflight_results",
                    "instance_source_freshness",
                    "company_capabilities",
                    "company_preflight_results",
                    "source_freshness",
                },
                set(DEFAULT_COLLECTIONS),
            )
            self.assertEqual(
                Path(directory) / "state" / "objects",
                bundle.state_objects.directory,
            )
            self.assertEqual(
                Path(directory) / "state" / "source-events",
                bundle.source_events.directory,
            )


if __name__ == "__main__":
    unittest.main()
