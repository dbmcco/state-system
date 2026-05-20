from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import InstancePreflightRuntime
from state_system.instance_source_freshness import InstanceSourceFreshnessRuntime
from state_system.instance_understanding_surface import (
    build_instance_understanding_surface_read_model,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "instance-capability"


class InstanceUnderstandingSurfaceTests(unittest.TestCase):
    def test_surface_rolls_instance_capability_and_federated_indexes_together(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-braydon-personal.json")]
            )

            read_model = build_instance_understanding_surface_read_model(stores)

        self.assertEqual("instance_understanding_surface_read_model", read_model["id"])
        self.assertFalse(read_model["invariant"]["surface_executes_retrieval"])
        self.assertIn("index.personal.agentmem.memory", read_model["index_refs"])
        self.assertIn(
            "index.personal.relationship_substrate.network",
            read_model["index_refs"],
        )
        self.assertIn(
            "gap.state_instance.braydon_personal.connector.personal.lfw_state_system.access_missing",
            read_model["source_gap_refs"],
        )
        personal = read_model["instances"][0]
        self.assertEqual("state_instance.braydon_personal", personal["instance_ref"])
        self.assertEqual("entity.braydon", personal["primary_entity_ref"])
        self.assertEqual("person", personal["entity_kind"])
        federation_pack = _federation_pack(
            personal,
            "instance_federation_pack.personal_to_lfw_state",
        )
        self.assertEqual("instance_read", federation_pack["federation_mode"])
        self.assertFalse(
            federation_pack["materialization_policy"]["local_materialization"]
        )

    def test_surface_uses_instance_preflight_for_connector_access_status(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-braydon-personal.json")]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": (
                        "preflight.state_instance.braydon_personal."
                        "connector.personal.folio"
                    ),
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.folio",
                    "source_ref": "folio:tenant:personal",
                    "connector_type": "folio",
                    "status": "passed",
                    "checked_at": "2026-05-16T19:42:47Z",
                    "stale_after": "2026-05-16T20:42:47Z",
                    "evidence_refs": ["preflight:folio:passed"],
                }
            )

            read_model = build_instance_understanding_surface_read_model(stores)

        personal = read_model["instances"][0]
        folio = next(
            source
            for source in personal["source_readiness"]
            if source["connector_ref"] == "connector.personal.folio"
        )
        self.assertEqual("passed", folio["access_status"])
        self.assertEqual("usable_with_freshness_gap", folio["understanding_status"])
        self.assertEqual(
            "preflight:folio:passed",
            folio["preflight_records"][0]["evidence_refs"][0],
        )

    def test_surface_uses_instance_freshness_for_ready_status(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-braydon-personal.json")]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": (
                        "preflight.state_instance.braydon_personal."
                        "connector.personal.folio"
                    ),
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.folio",
                    "source_ref": "folio:tenant:personal",
                    "connector_type": "folio",
                    "status": "passed",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "evidence_refs": ["preflight:folio:passed"],
                }
            )
            InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.folio",
                    "source_ref": "folio:tenant:personal",
                    "connector_type": "folio",
                    "status": "fresh",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "folio.indexed_at:2026-05-17T10:14:00Z",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "lag_seconds": 60,
                    "evidence_refs": ["paia:freshness:folio:fresh"],
                }
            )

            read_model = build_instance_understanding_surface_read_model(stores)

        personal = read_model["instances"][0]
        folio = next(
            source
            for source in personal["source_readiness"]
            if source["connector_ref"] == "connector.personal.folio"
        )
        self.assertEqual("fresh", folio["freshness_status"])
        self.assertEqual("ready", folio["understanding_status"])
        self.assertEqual(
            "paia:freshness:folio:fresh",
            folio["freshness_record"]["evidence_refs"][0],
        )

    def test_surface_preserves_planned_preflight_as_access_gap(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-braydon-personal.json")]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": (
                        "preflight.state_instance.braydon_personal."
                        "connector.personal.agentmem"
                    ),
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.agentmem",
                    "source_ref": "agentmem:tenant:braydon",
                    "connector_type": "agentmem",
                    "status": "planned",
                    "checked_at": "2026-05-16T19:42:47Z",
                    "stale_after": "2026-05-16T20:42:47Z",
                    "evidence_refs": ["preflight:agentmem:planned"],
                }
            )

            read_model = build_instance_understanding_surface_read_model(stores)

        personal = read_model["instances"][0]
        agentmem = next(
            source
            for source in personal["source_readiness"]
            if source["connector_ref"] == "connector.personal.agentmem"
        )
        self.assertEqual("planned", agentmem["access_status"])
        self.assertIn(
            "gap.state_instance.braydon_personal.connector.personal.agentmem.access_planned",
            read_model["source_gap_refs"],
        )

    def test_surface_preserves_garmin_ready_and_spotify_freshness_gap(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-braydon-personal.json")]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": (
                        "preflight.state_instance.braydon_personal."
                        "connector.personal.garmin_connect"
                    ),
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.garmin_connect",
                    "source_ref": "garmin-connect:account:braydon",
                    "connector_type": "garmin_connect",
                    "status": "passed",
                    "checked_at": "2026-05-17T18:37:18Z",
                    "stale_after": "2026-05-17T19:37:18Z",
                    "evidence_refs": ["preflight:garmin_connect:passed"],
                }
            )
            InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.garmin_connect",
                    "source_ref": "garmin-connect:account:braydon",
                    "connector_type": "garmin_connect",
                    "status": "fresh",
                    "checked_at": "2026-05-17T18:37:18Z",
                    "source_watermark": (
                        "garmin.daily_summary.synced_at:2026-05-17T18:23:58Z"
                    ),
                    "stale_after": "2026-05-17T19:37:18Z",
                    "evidence_refs": ["freshness:garmin_connect:fresh"],
                    "index_refs": ["index.personal.garmin_connect.activity"],
                }
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": (
                        "preflight.state_instance.braydon_personal."
                        "connector.personal.spotify"
                    ),
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.spotify",
                    "source_ref": "spotify:account:braydon",
                    "connector_type": "spotify",
                    "status": "passed",
                    "checked_at": "2026-05-17T19:48:00Z",
                    "stale_after": "2026-05-17T20:48:00Z",
                    "evidence_refs": ["preflight:spotify:history_cache"],
                }
            )
            InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.spotify",
                    "source_ref": "spotify:account:braydon",
                    "connector_type": "spotify",
                    "status": "stale",
                    "checked_at": "2026-05-17T19:48:00Z",
                    "source_watermark": (
                        "spotify.assistant_postgres.spotify_listening_records."
                        "played_at:2026-02-15T15:09:00Z"
                    ),
                    "stale_after": "2026-02-16T15:09:00Z",
                    "evidence_refs": ["freshness:spotify:stale"],
                    "index_refs": ["index.personal.spotify.listening"],
                }
            )

            read_model = build_instance_understanding_surface_read_model(stores)

        personal = read_model["instances"][0]
        garmin = next(
            source
            for source in personal["source_readiness"]
            if source["connector_ref"] == "connector.personal.garmin_connect"
        )
        spotify = next(
            source
            for source in personal["source_readiness"]
            if source["connector_ref"] == "connector.personal.spotify"
        )
        self.assertEqual("passed", garmin["access_status"])
        self.assertEqual("passed", spotify["access_status"])
        self.assertEqual("declared", garmin["index_status"])
        self.assertEqual("declared", spotify["index_status"])
        self.assertEqual("ready", garmin["understanding_status"])
        self.assertEqual("usable_with_freshness_gap", spotify["understanding_status"])
        self.assertEqual("source_module.garmin_connect", garmin["source_module_ref"])
        self.assertEqual("local_sync", garmin["module_mode"])
        self.assertEqual(
            "garmin.daily_summary.synced_at:2026-05-17T18:23:58Z",
            garmin["source_watermark"],
        )
        self.assertEqual("2026-05-17T19:37:18Z", garmin["stale_after"])
        self.assertEqual("source_module.spotify", spotify["source_module_ref"])
        self.assertEqual("historical_cache", spotify["module_mode"])
        self.assertEqual(
            "source_module.spotify.gap_behavior",
            spotify["gap_behavior_ref"],
        )
        self.assertEqual("usable_with_freshness_gap", spotify["usable_access_status"])
        self.assertNotIn(
            "gap.state_instance.braydon_personal.connector.personal.garmin_connect.access_planned",
            read_model["source_gap_refs"],
        )
        self.assertIn(
            "gap.state_instance.braydon_personal.connector.personal.spotify.freshness_stale",
            read_model["source_gap_refs"],
        )

    def test_cli_writes_instance_understanding_surface(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            seed_output = StringIO()
            seed_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-capability-seed",
                    str(PACK_DIR / "instance-braydon-personal.json"),
                ],
                stdout=seed_output,
            )
            self.assertEqual(0, seed_code, seed_output.getvalue())

            read_output = StringIO()
            read_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-understanding-surface-read",
                    "--output-dir",
                    output_dir,
                ],
                stdout=read_output,
            )

            self.assertEqual(0, read_code, read_output.getvalue())
            payload = json.loads(read_output.getvalue())
            read_model_path = Path(payload["read_model_path"])
            self.assertEqual(
                "instance-understanding-surface-read-model.json",
                read_model_path.name,
            )
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual("instance_understanding_surface_read_model", read_model["id"])
            self.assertEqual(
                ["state_instance.braydon_personal"],
                [instance["instance_ref"] for instance in read_model["instances"]],
            )
            folio = next(
                source
                for source in read_model["instances"][0]["source_readiness"]
                if source["connector_ref"] == "connector.personal.folio"
            )
            self.assertEqual("source_module.folio", folio["source_module_ref"])
            self.assertEqual(
                "source_module_registry.core_connectors",
                folio["module_registry_ref"],
            )
            self.assertEqual("source_module.folio.preflight", folio["preflight_contract_ref"])


def _federation_pack(instance: dict, pack_id: str):
    matches = [
        pack
        for pack in instance.get("federation_packs", [])
        if pack["id"] == pack_id
    ]
    if not matches:
        raise AssertionError(f"{pack_id} not found")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
