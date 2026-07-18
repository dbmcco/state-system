from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli


ROOT = Path(__file__).resolve().parents[1]


class CliModelOperableTests(unittest.TestCase):
    def test_json_handshake_returns_typed_dispatcher_envelope(self):
        output = StringIO()

        code = cli.main(
            ["--project-root", str(ROOT), "--json", "handshake"],
            stdout=output,
        )

        payload = json.loads(output.getvalue())
        self.assertEqual(0, code)
        self.assertEqual("state-system.v1", payload["protocol_version"])
        self.assertEqual("handshake", payload["operation"])
        self.assertEqual("ok", payload["status"])
        self.assertIn("capabilities", payload["data"])
        self.assertEqual([], payload["errors"])

    def test_format_json_malformed_dispatch_returns_repairable_error_without_traceback(self):
        output = StringIO()

        code = cli.main(
            [
                "--project-root",
                str(ROOT),
                "--format",
                "json",
                "dispatch",
                "not-an-operation",
            ],
            stdout=output,
        )

        text = output.getvalue()
        payload = json.loads(text)
        self.assertEqual(1, code)
        self.assertNotIn("Traceback", text)
        self.assertEqual("error", payload["status"])
        self.assertEqual("unknown_operation", payload["errors"][0]["code"])
        self.assertTrue(payload["errors"][0]["retryable"])
        self.assertTrue(payload["errors"][0]["next_steps"])
        self.assertTrue(payload["errors"][0]["safe_examples"])

    def test_json_acknowledge_gap_is_internal_write_and_not_authorization(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "--json",
                    "acknowledge-gap",
                    "gap:source.stale",
                    "--request-id",
                    "request-gap-cli",
                    "--idempotency-key",
                    "idem-gap-cli",
                    "--acknowledged-by-ref",
                    "actor:agent",
                    "--reason",
                    "reviewed and disclosed",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            self.assertEqual(0, code)
            self.assertEqual("acknowledge_gap", payload["operation"])
            self.assertEqual("ok", payload["status"])
            self.assertFalse(payload["data"]["authorizes"])
            self.assertIn("retain_until", payload["data"]["acknowledgement"])
            self.assertIn("retain_until", payload["receipt"])
            self.assertNotIn("authorization_ref", payload["receipt"])


if __name__ == "__main__":
    unittest.main()
