import unittest

from state_system.cli import _parser


class ModelOperableHelpTests(unittest.TestCase):
    def test_help_teaches_effects_examples_repairs_acknowledgement_retention_and_authorization(self):
        help_text = _parser().format_help().lower()

        for phrase in (
            "read-only",
            "internal-write",
            "external-effect",
            "example",
            "repair",
            "acknowledge_gap",
            "retention",
            "does not authorize",
        ):
            self.assertIn(phrase, help_text)


if __name__ == "__main__":
    unittest.main()
