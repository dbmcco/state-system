from io import StringIO
import json
from pathlib import Path
import unittest

from state_system import cli


ROOT = Path(__file__).resolve().parents[2]


class CliErrorRepairGuidanceTests(unittest.TestCase):
    def test_missing_acknowledgement_arguments_are_structured_and_actionable(self):
        output = StringIO()

        code = cli.main(
            [
                "--project-root",
                str(ROOT),
                "--json",
                "acknowledge-gap",
                "gap:source.stale",
            ],
            stdout=output,
        )

        text = output.getvalue()
        payload = json.loads(text)
        self.assertEqual(1, code)
        self.assertNotIn("Traceback", text)
        self.assertEqual("error", payload["status"])
        error = payload["errors"][0]
        self.assertEqual("invalid_request", error["code"])
        self.assertIn("idempotency_key", error["expected_shape"])
        self.assertTrue(error["safe_examples"])
        self.assertTrue(error["next_steps"])


if __name__ == "__main__":
    unittest.main()
