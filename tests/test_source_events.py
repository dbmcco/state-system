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
            self.assertEqual(
                ["source.linear.southern-abrasives-won"],
                stores.source_events.list_ids(),
            )

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

    def test_same_native_source_event_id_is_duplicate_even_with_new_key(self):
        source_event = load_json(
            ROOT / "examples" / "source-linear-southern-abrasives-won.json"
        )
        duplicate = deepcopy(source_event)
        duplicate["id"] = "source.linear.same-native-event-id"
        duplicate["idempotency"]["key"] = "linear-event-replayed-with-new-key"

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            ingestor = SourceEventIngestor(
                stores,
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            )

            ingestor.ingest(source_event)
            result = ingestor.ingest(duplicate)

            duplicate_record = stores.source_events.read(duplicate["id"])
            self.assertFalse(result.created)
            self.assertIsNone(result.trigger)
            self.assertEqual(source_event["id"], result.duplicate_of)
            self.assertEqual("source_event_id", result.duplicate_reason)
            self.assertEqual(source_event["id"], duplicate_record["duplicate_of_ref"])

    def test_same_field_transition_is_duplicate_even_with_later_observed_at(self):
        source_event = load_json(
            ROOT / "examples" / "source-linear-southern-abrasives-won.json"
        )
        duplicate = deepcopy(source_event)
        duplicate["id"] = "source.linear.same-transition-later-observed"
        duplicate["source_event_id"] = "linear-event-replayed-later-observed"
        duplicate["observed_at"] = "2026-04-28T17:05:00Z"
        duplicate["idempotency"] = {
            "key": "linear-event-replayed-later-observed",
            "dedupe_strategy": "source_ref_and_change",
        }

        with TemporaryDirectory() as directory:
            ingestor = SourceEventIngestor(
                StateStoreBundle(Path(directory)),
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            )

            ingestor.ingest(source_event)
            result = ingestor.ingest(duplicate)

            self.assertFalse(result.created)
            self.assertIsNone(result.trigger)
            self.assertEqual(source_event["id"], result.duplicate_of)
            self.assertEqual("field_transition", result.duplicate_reason)

    def test_full_sync_replay_after_partial_sync_is_recorded_without_new_trigger(self):
        partial = load_json(ROOT / "examples" / "source-linear-southern-abrasives-won.json")
        partial["id"] = "source.linear.partial-stage-won"
        partial["source_event_id"] = "linear-event-stage-won-partial"
        partial["idempotency"] = {
            "key": "linear-event-stage-won-partial",
            "dedupe_strategy": "source_event_id",
            "semantic_fingerprint": "linear:deal:southern-abrasives:stage:proposal->won",
        }
        partial["sync_context"] = {
            "sync_id": "linear-partial-sync",
            "source_watermark": "2026-04-28T16:05:00Z",
            "partial": True,
            "confidence": "low",
        }
        full = deepcopy(partial)
        full["id"] = "source.linear.full-stage-won"
        full["source_event_id"] = "linear-event-stage-won-full"
        full["idempotency"]["key"] = "linear-event-stage-won-full"
        full["sync_context"] = {
            "sync_id": "linear-full-sync",
            "source_watermark": "2026-04-28T16:10:00Z",
            "partial": False,
            "confidence": "high",
        }

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            ingestor = SourceEventIngestor(
                stores,
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            )

            ingestor.ingest(partial)
            result = ingestor.ingest(full)

            duplicate_record = stores.source_events.read(full["id"])
            self.assertFalse(result.created)
            self.assertIsNone(result.trigger)
            self.assertEqual(partial["id"], result.duplicate_of)
            self.assertEqual("semantic_fingerprint", result.duplicate_reason)
            self.assertEqual(full["sync_context"], duplicate_record["sync_context"])
            self.assertEqual(partial["id"], duplicate_record["duplicate_of_ref"])

    def test_out_of_order_source_watermark_is_surfaced_without_blocking_event(self):
        newer = load_json(ROOT / "examples" / "source-linear-southern-abrasives-won.json")
        older = deepcopy(newer)
        newer["id"] = "source.linear.newer-watermark"
        newer["source_event_id"] = "linear-event-newer-watermark"
        newer["change"]["new_value"] = "closed_won"
        newer["idempotency"] = {
            "key": "linear-event-newer-watermark",
            "dedupe_strategy": "source_event_id",
        }
        newer["sync_context"]["source_watermark"] = "2026-04-28T16:10:00Z"
        older["id"] = "source.linear.older-watermark"
        older["source_event_id"] = "linear-event-older-watermark"
        older["change"]["new_value"] = "won"
        older["idempotency"] = {
            "key": "linear-event-older-watermark",
            "dedupe_strategy": "source_event_id",
        }
        older["sync_context"]["source_watermark"] = "2026-04-28T16:00:00Z"

        with TemporaryDirectory() as directory:
            ingestor = SourceEventIngestor(
                StateStoreBundle(Path(directory)),
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            )

            ingestor.ingest(newer)
            result = ingestor.ingest(older)

            self.assertTrue(result.created)
            self.assertEqual("out_of_order", result.watermark_status)
            self.assertEqual(
                "out_of_order",
                result.evidence_context["source_event"]["watermark_status"],
            )

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
            self.assertEqual(
                source_event["candidate_state_refs"],
                result.trigger["candidate_state_refs"],
            )

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
