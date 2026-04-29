from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from state_system.contracts import load_json, schema_for_example
from state_system.stores import JsonObject


class ReviewFixtureNotFoundError(KeyError):
    """Raised when no fixture output exists for a review packet."""


class FixtureReviewer:
    def __init__(self, outputs_by_review_packet_id: dict[str, JsonObject]):
        self.outputs_by_review_packet_id = {
            key: deepcopy(value) for key, value in outputs_by_review_packet_id.items()
        }

    @classmethod
    def from_examples(cls, examples_dir: Path) -> "FixtureReviewer":
        outputs = {}
        for path in sorted(examples_dir.glob("*.json")):
            if schema_for_example(path.name) != "model-proposal-output.schema.json":
                continue
            output = load_json(path)
            outputs[output["review_packet_id"]] = output
        return cls(outputs)

    def review(self, review_packet: JsonObject) -> JsonObject:
        packet_id = review_packet["id"]
        if packet_id not in self.outputs_by_review_packet_id:
            raise ReviewFixtureNotFoundError(packet_id)
        return deepcopy(self.outputs_by_review_packet_id[packet_id])
