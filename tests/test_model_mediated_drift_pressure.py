from pathlib import Path
import unittest

from state_system.contracts import load_json


ROOT = Path(__file__).resolve().parents[1]
APP_INTEGRATIONS = ROOT / "examples" / "app-integrations"
BOUNDARY_DOC = ROOT / "docs" / "model-mediated-drift-pressure-suite.md"


def _walk_json(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key, nested
            yield from _walk_json(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_json(nested)


class ModelMediatedDriftPressureTests(unittest.TestCase):
    def test_boundary_doctrine_is_documented_for_future_app_work(self):
        self.assertTrue(
            BOUNDARY_DOC.exists(),
            "model-mediated drift suite needs an explicit boundary doctrine doc",
        )

        text = BOUNDARY_DOC.read_text(encoding="utf-8").lower()

        self.assertIn("model-owned judgment", text)
        self.assertIn("deterministic code", text)
        self.assertIn("hidden scoring", text)
        self.assertIn("regex routing", text)
        self.assertIn("approved deviation", text)
        self.assertIn("pressure-suite rule", text)

    def test_app_conformance_notes_preserve_model_owned_judgment(self):
        conformance_paths = sorted(APP_INTEGRATIONS.glob("conformance-*.json"))

        self.assertGreater(len(conformance_paths), 0)
        for path in conformance_paths:
            with self.subTest(path=path.name):
                note = load_json(path)

                self.assertTrue(note["passed"])
                self.assertGreater(len(note["evidence_refs"]), 0)
                self.assertGreater(len(note["model_owned_judgments"]), 0)
                self.assertEqual([], note["deterministic_judgment_rules"])

    def test_app_model_outputs_explain_the_judgment_boundary(self):
        output_paths = sorted(APP_INTEGRATIONS.glob("*-model-proposal-output-*.json"))

        self.assertGreater(len(output_paths), 0)
        for path in output_paths:
            with self.subTest(path=path.name):
                output = load_json(path)
                observations = " ".join(output["observations"]).lower()

                self.assertIn("model interpretation", observations)
                self.assertTrue(
                    any(
                        marker in observations
                        for marker in ("deterministic", "regex", "threshold", "score")
                    ),
                    f"{path.name} must name the deterministic drift risk it avoids",
                )

    def test_app_fixture_payloads_do_not_add_hidden_rule_fields(self):
        forbidden_keys = {
            "bant_score",
            "classification_rules",
            "fit_score",
            "keyword_rule",
            "keyword_rules",
            "regex",
            "routing_regex",
            "score",
            "scores",
            "scoring_rule",
            "threshold",
            "thresholds",
            "tone_score",
        }

        for path in sorted(APP_INTEGRATIONS.glob("*.json")):
            document = load_json(path)
            with self.subTest(path=path.name):
                hidden_rule_keys = sorted(
                    key for key, _ in _walk_json(document) if key in forbidden_keys
                )

                self.assertEqual([], hidden_rule_keys)


if __name__ == "__main__":
    unittest.main()
