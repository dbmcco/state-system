from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from state_system.contracts import load_json
from state_system.instance_capability import (
    InstanceCapabilityRuntime,
    build_instance_capability_read_model,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples/instance-capability"


class InstanceCapabilityRuntimeTests(unittest.TestCase):
    def test_seeded_instance_packs_build_instance_read_model(self):
        with tempfile.TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceCapabilityRuntime(stores)

            result = runtime.seed(
                [
                    load_json(PACK_DIR / "instance-acme.json"),
                    load_json(PACK_DIR / "instance-acme-ops.json"),
                ]
            )
            read_model = build_instance_capability_read_model(runtime.list_packs())

        self.assertEqual(2, result["count"])
        self.assertEqual(
            ["state_instance.acme", "state_instance.acme_ops"],
            [instance["instance_ref"] for instance in read_model["instances"]],
        )
        self.assertIn("index.personal.agentmem.memory", read_model["index_refs"])
        self.assertIn(
            "index.personal.relationship_substrate.network",
            read_model["index_refs"],
        )
        self.assertIn(
            "state-system-instance:state_instance.acme",
            read_model["source_refs"],
        )


if __name__ == "__main__":
    unittest.main()
