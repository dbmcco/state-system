from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json
from state_system.instance_capability import InstanceCapabilityRuntime
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


if __name__ == "__main__":
    unittest.main()
