from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, schema_for_example, validate_schema
from state_system.entity_current_state import (
    EntityCurrentStateRuntime,
    build_entity_current_state_read_model,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "entity-current-state-record.schema.json"


def _card(**overrides):
    card = {
        "entity_id": "synthyra",
        "entity_name": "Synthyra",
        "north_star": "Metabolic engineering destination (durable long-term direction).",
        "current_priority": "Get to market with known tech.",
        "owner": "Braydon",
        "waiting_on": "",
        "braydon_next_action": "Push ERIS deliverables and buyer discovery.",
        "effective_at": "2026-06-15T00:00:00Z",
        "stale_after": "2026-06-23T00:00:00Z",
        "supersedes": None,
        "source_refs": ["wkm-status:status/north-star-load-map-2026-06-16.md"],
        "confidence": "high",
        "status": "active",
        "generated_at": "2026-06-16T18:00:00Z",
        "generated_by": "braydon",
    }
    card.update(overrides)
    return card


class EntityCurrentStateSchemaTests(unittest.TestCase):
    def test_minimal_card_is_schema_valid(self):
        runtime_record = EntityCurrentStateRuntime.__module__  # import sanity
        self.assertTrue(runtime_record)
        record = _card()
        record["id"] = "entity_current_state.synthyra.2026-06-15T00-00-00Z"
        errors = validate_schema(record, load_json(SCHEMA))
        self.assertEqual([], errors)

    def test_missing_required_field_is_rejected(self):
        record = _card()
        record["id"] = "entity_current_state.synthyra.2026-06-15T00-00-00Z"
        del record["north_star"]
        errors = validate_schema(record, load_json(SCHEMA))
        self.assertTrue(any("north_star" in error for error in errors))

    def test_confidence_enum_is_enforced(self):
        record = _card(confidence="0.91")
        record["id"] = "x"
        errors = validate_schema(record, load_json(SCHEMA))
        self.assertTrue(any("confidence" in error for error in errors))

    def test_schema_routing_for_record_examples(self):
        self.assertEqual(
            "entity-current-state-record.schema.json",
            schema_for_example("entity-current-state-sample.json"),
        )


class EntityCurrentStateRuntimeTests(unittest.TestCase):
    def test_record_persists_and_reads_back_with_derived_id(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = EntityCurrentStateRuntime(stores)
            record = runtime.record(_card())

            self.assertEqual(
                "entity_current_state.synthyra.2026-06-15T00-00-00Z", record["id"]
            )
            path = (
                Path(directory)
                / "state"
                / "entity-current-state"
                / f"{record['id']}.json"
            )
            self.assertTrue(path.exists())
            self.assertEqual(record, runtime.read(record["id"]))

    def test_store_is_append_only_supersede_keeps_prior_record(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = EntityCurrentStateRuntime(stores)
            prior = runtime.record(_card())
            newer = runtime.record(
                _card(
                    effective_at="2026-06-16T00:00:00Z",
                    current_priority="Decision-support for what to validate next.",
                    supersedes=prior["id"],
                )
            )

            self.assertNotEqual(prior["id"], newer["id"])
            both = {record["id"] for record in runtime.list_records()}
            self.assertIn(prior["id"], both)
            self.assertIn(newer["id"], both)

    def test_record_rejects_overwriting_an_existing_record(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = EntityCurrentStateRuntime(stores)
            runtime.record(_card())
            with self.assertRaises(Exception):
                runtime.record(_card())


class EntityCurrentStateReadModelTests(unittest.TestCase):
    def _stores_with(self, *cards):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        stores = StateStoreBundle(Path(directory.name))
        runtime = EntityCurrentStateRuntime(stores)
        for card in cards:
            runtime.record(card)
        return stores

    def test_superseded_record_is_excluded_from_active_view(self):
        stores = self._stores_with(_card())
        runtime = EntityCurrentStateRuntime(stores)
        prior_id = runtime.list_records()[0]["id"]
        runtime.record(
            _card(
                effective_at="2026-06-16T00:00:00Z",
                supersedes=prior_id,
            )
        )

        model = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        active_ids = {card["id"] for card in model["active_cards"]}
        self.assertNotIn(prior_id, active_ids)
        self.assertIn(prior_id, model["superseded_record_refs"])
        self.assertEqual(["synthyra"], model["entity_ids"])

    def test_explicit_superseded_status_is_excluded(self):
        stores = self._stores_with(
            _card(status="superseded", effective_at="2026-06-10T00:00:00Z"),
            _card(),
        )
        model = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        self.assertEqual(1, len(model["active_cards"]))

    def test_retracted_record_is_excluded_and_listed(self):
        stores = self._stores_with(
            _card(status="retracted", effective_at="2026-06-10T00:00:00Z"),
        )
        model = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        self.assertEqual([], model["active_cards"])
        self.assertEqual(1, len(model["retracted_record_refs"]))

    def test_card_past_stale_after_is_flagged_stale_with_decay_warning(self):
        stores = self._stores_with(_card(stale_after="2026-06-16T00:00:00Z"))
        model = build_entity_current_state_read_model(
            stores, as_of="2026-06-17T00:00:00Z"
        )
        card = model["active_cards"][0]
        self.assertTrue(card["is_stale"])
        self.assertNotEqual("", card["decay_warning"])

    def test_card_before_stale_after_is_not_stale(self):
        stores = self._stores_with(_card(stale_after="2026-06-23T00:00:00Z"))
        model = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        card = model["active_cards"][0]
        self.assertFalse(card["is_stale"])
        self.assertEqual("", card["decay_warning"])

    def test_card_before_effective_at_is_flagged_not_yet_effective(self):
        stores = self._stores_with(_card(effective_at="2026-06-20T00:00:00Z"))
        model = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        self.assertTrue(model["active_cards"][0]["not_yet_effective"])

    def test_synthyra_two_horizon_card_keeps_both_north_star_and_priority(self):
        # Braydon's correction: durable north_star AND near-term current_priority
        # are both true at different horizons; the card must carry both verbatim,
        # and must NOT be marked superseded or stale near-term.
        stores = self._stores_with(
            _card(
                north_star="Metabolic engineering destination (durable long-term direction).",
                current_priority="Get to market with known tech; near-term decision-support for what to validate next.",
                stale_after="2026-06-23T00:00:00Z",
            )
        )
        model = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        card = model["active_cards"][0]
        self.assertIn("metabolic", card["north_star"].lower())
        self.assertIn("known tech", card["current_priority"].lower())
        self.assertEqual("active", card["status"])
        self.assertFalse(card["is_stale"])
        self.assertEqual([], model["superseded_record_refs"])

    def test_two_active_heads_for_one_entity_are_surfaced_as_conflict(self):
        stores = self._stores_with(
            _card(effective_at="2026-06-15T00:00:00Z"),
            _card(effective_at="2026-06-16T00:00:00Z"),
        )
        model = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        # Both are active heads (no supersedes link) -> mechanically surfaced,
        # not silently resolved (that would be a model-agency violation).
        self.assertEqual(2, len(model["active_cards"]))
        self.assertIn("synthyra", model["conflicting_entity_ids"])

    def test_resolution_is_deterministic_for_a_fixed_as_of(self):
        stores = self._stores_with(_card())
        first = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        second = build_entity_current_state_read_model(
            stores, as_of="2026-06-16T18:00:00Z"
        )
        self.assertEqual(first, second)


class EntityCurrentStateCliTests(unittest.TestCase):
    def test_record_then_export_writes_read_model(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            stdout = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    str(root),
                    "entity-current-state-record",
                    "--entity-id",
                    "synthyra",
                    "--entity-name",
                    "Synthyra",
                    "--north-star",
                    "Metabolic engineering destination (durable).",
                    "--current-priority",
                    "Get to market with known tech.",
                    "--owner",
                    "Braydon",
                    "--waiting-on",
                    "",
                    "--braydon-next-action",
                    "Push ERIS deliverables.",
                    "--effective-at",
                    "2026-06-15T00:00:00Z",
                    "--stale-after",
                    "2026-06-23T00:00:00Z",
                    "--source-ref",
                    "wkm-status:status/north-star-load-map-2026-06-16.md",
                    "--confidence",
                    "high",
                    "--status",
                    "active",
                    "--generated-at",
                    "2026-06-16T18:00:00Z",
                    "--generated-by",
                    "braydon",
                ],
                stdout=stdout,
            )
            self.assertEqual(0, code, stdout.getvalue())
            self.assertTrue(json.loads(stdout.getvalue())["ok"])

            export_stdout = StringIO()
            export_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    str(root),
                    "entity-current-state-export",
                    "--as-of",
                    "2026-06-16T18:00:00Z",
                    "--output-dir",
                    str(root / "entity-current-state"),
                ],
                stdout=export_stdout,
            )
            self.assertEqual(0, export_code, export_stdout.getvalue())
            read_model_path = (
                root / "entity-current-state" / "entity-current-state-read-model.json"
            )
            self.assertTrue(read_model_path.exists())
            model = load_json(read_model_path)
            self.assertEqual("entity_current_state_read_model", model["id"])
            self.assertEqual(["synthyra"], model["entity_ids"])


if __name__ == "__main__":
    unittest.main()
