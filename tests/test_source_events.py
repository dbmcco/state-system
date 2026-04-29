from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.runner import SourceEventIngestor, SourceEventValidationError
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class SourceEventIngestionTests(unittest.TestCase):
    def test_replaying_fixture_source_event_is_idempotent(self):
        source_event = load_json(
            ROOT / "examples" / "source-linear-southern-abrasives-won.json"
        )
        schema = load_json(ROOT / "schemas" / "source-event.schema.json")

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            ingestor = SourceEventIngestor(stores, schema)

            first = ingestor.ingest(source_event)
            second = ingestor.ingest(source_event)

            self.assertTrue(first.created)
            self.assertEqual("trigger.linear.southern-abrasives-won", first.trigger["id"])
            self.assertFalse(second.created)
            self.assertIsNone(second.trigger)
            self.assertEqual("source.linear.southern-abrasives-won", second.duplicate_of)
            self.assertEqual(["source.linear.southern-abrasives-won"], stores.source_events.list_ids())

    def test_same_idempotency_key_with_different_record_id_does_not_create_trigger(self):
        source_event = load_json(
            ROOT / "examples" / "source-linear-southern-abrasives-won.json"
        )
        duplicate = deepcopy(source_event)
        duplicate["id"] = "source.linear.southern-abrasives-won-replayed"

        with TemporaryDirectory() as directory:
            ingestor = SourceEventIngestor(
                StateStoreBundle(Path(directory)),
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            )

            first = ingestor.ingest(source_event)
            second = ingestor.ingest(duplicate)

            self.assertIsNotNone(first.trigger)
            self.assertFalse(second.created)
            self.assertIsNone(second.trigger)
            self.assertEqual(source_event["id"], second.duplicate_of)

    def test_partial_sync_context_survives_into_trigger_and_evidence_context(self):
        source_event = load_json(
            ROOT / "examples" / "source-linear-southern-abrasives-won.json"
        )
        source_event["id"] = "source.linear.partial-sync"
        source_event["idempotency"]["key"] = "linear-event-partial-sync"
        source_event["sync_context"] = {
            "sync_id": "linear-partial-sync",
            "partial": True,
            "confidence": "low",
        }

        with TemporaryDirectory() as directory:
            ingestor = SourceEventIngestor(
                StateStoreBundle(Path(directory)),
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            )

            result = ingestor.ingest(source_event)

            self.assertEqual(
                source_event["sync_context"],
                result.trigger["payload"]["sync_context"],
            )
            self.assertEqual(
                source_event["sync_context"],
                result.evidence_context["source_event"]["sync_context"],
            )

    def test_ingestion_does_not_choose_persona_or_salience(self):
        source_event = load_json(
            ROOT / "examples" / "source-linear-southern-abrasives-won.json"
        )

        with TemporaryDirectory() as directory:
            ingestor = SourceEventIngestor(
                StateStoreBundle(Path(directory)),
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            )

            result = ingestor.ingest(source_event)

            self.assertNotIn("persona_ref", result.trigger)
            self.assertNotIn("opportunity", result.trigger["payload"])
            self.assertEqual(source_event["candidate_state_refs"], result.trigger["candidate_state_refs"])

    def test_invalid_source_event_is_rejected_without_persisting(self):
        source_event = load_json(
            ROOT / "examples" / "source-linear-southern-abrasives-won.json"
        )
        del source_event["idempotency"]

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            ingestor = SourceEventIngestor(
                stores,
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            )

            with self.assertRaises(SourceEventValidationError):
                ingestor.ingest(source_event)

            self.assertEqual([], stores.source_events.list_ids())


if __name__ == "__main__":
    unittest.main()
