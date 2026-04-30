from pathlib import Path
import unittest

from state_system.contracts import ExampleIndex, validate_all_examples, validate_trace


ROOT = Path(__file__).resolve().parents[1]


def load_schema(name: str):
    import json

    with (ROOT / "schemas" / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class ContractHarnessTests(unittest.TestCase):
    def test_all_examples_validate_against_known_schemas(self):
        results = validate_all_examples(ROOT)

        self.assertGreater(len(results), 0)
        self.assertEqual([], [result for result in results if not result.ok])

    def test_first_deployment_traces_are_consistent(self):
        index = ExampleIndex.load(ROOT / "examples")

        traces = [
            [
                "examples/laura-campaign-audience-trigger.json",
                "examples/laura-model-review-packet.json",
                "examples/laura-model-proposal-output.json",
                "examples/laura-commit-result.json",
                "examples/marketing-campaign-audience-journal-entry.json",
                "examples/laura-agent-memory-entry.json",
                "examples/laura-review-signal.json",
            ],
            [
                "examples/patrick-stale-contract-trigger.json",
                "examples/patrick-model-review-packet.json",
                "examples/patrick-model-proposal-output.json",
                "examples/patrick-commit-result.json",
                "examples/patrick-contract-journal-entry.json",
                "examples/patrick-agent-memory-entry.json",
                "examples/patrick-review-signal.json",
            ],
            [
                "examples/patrick-github-launch-readiness-trigger.json",
                "examples/patrick-github-launch-readiness-model-review-packet.json",
                "examples/patrick-github-launch-readiness-model-proposal-output.json",
                "examples/patrick-github-launch-readiness-commit-result.json",
                "examples/patrick-github-capability-journal-entry.json",
                "examples/patrick-github-obligation-journal-entry.json",
                "examples/patrick-github-launch-readiness-agent-memory-entry.json",
                "examples/patrick-github-launch-readiness-review-signal.json",
            ],
            [
                "examples/source-linear-southern-abrasives-won.json",
                "examples/linear-southern-abrasives-won-trigger.json",
                "examples/linear-southern-abrasives-won-model-review-packet.json",
                "examples/linear-southern-abrasives-won-model-proposal-output.json",
                "examples/linear-southern-abrasives-won-commit-result.json",
                "examples/recent-linear-southern-abrasives-won.json",
                "examples/laura-southern-abrasives-opportunity-context-package.json",
                "examples/laura-southern-abrasives-opportunity-review-packet.json",
                "examples/laura-southern-abrasives-opportunity-model-output.json",
                "examples/laura-southern-abrasives-opportunity-commit-result.json",
            ],
            [
                "examples/source-model-mediated-intent-routing-violation.json",
                "examples/model-mediated-intent-routing-violation-trigger.json",
                "examples/model-mediated-intent-routing-violation-model-review-packet.json",
                "examples/model-mediated-intent-routing-violation-model-proposal-output.json",
            ],
        ]

        failures = []
        for trace in traces:
            failures.extend(validate_trace(ROOT, trace, index=index))

        self.assertEqual([], failures)

    def test_commit_refs_resolve_without_interpreting_business_meaning(self):
        index = ExampleIndex.load(ROOT / "examples")
        commit = index.by_id["commit.patrick.github-launch-readiness"]

        refs = (
            commit["accepted_journal_entry_refs"]
            + commit["accepted_memory_entry_refs"]
            + commit["materialized_snapshot_refs"]
        )

        self.assertGreater(len(commit["accepted_journal_entry_refs"]), 1)
        self.assertEqual([], [ref for ref in refs if ref not in index.by_id])

    def test_pressure_outcomes_are_representable_in_fixtures_and_schemas(self):
        index = ExampleIndex.load(ROOT / "examples")

        model_schema = load_schema("model-proposal-output.schema.json")
        commit_schema = load_schema("commit-result.schema.json")
        github_output = index.by_id["model_output.patrick.github-launch-readiness"]
        opportunity_commit = index.by_id["commit.laura.southern-abrasives-opportunity"]

        self.assertIn("no_op", model_schema["properties"]["decision"]["enum"])
        self.assertIn("no_op", commit_schema["properties"]["status"]["enum"])
        self.assertEqual("pending_approval", opportunity_commit["status"])
        self.assertGreater(len(opportunity_commit["pending_approvals"]), 0)
        self.assertGreater(len(github_output["state_proposals"]), 1)
        self.assertGreater(len(github_output["missing_evidence"]), 0)


if __name__ == "__main__":
    unittest.main()
