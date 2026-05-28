from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_schema
from state_system.source_adapters import git_commit_to_source_event
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class GitSourceAdapterTests(unittest.TestCase):
    def test_git_commit_metadata_becomes_valid_source_event(self):
        commit = {
            "sha": "abc123def456",
            "author_name": "Braydon McConnell",
            "author_email": "user@example.com",
            "authored_at": "2026-05-01T17:30:00Z",
            "subject": "feat: add runtime v0 CLI loop",
            "body": "Adds review, commit, recent, and package commands.",
            "changed_files": ["state_system/cli.py", "state_system/runtime.py"],
        }

        event = git_commit_to_source_event(
            commit,
            repo_ref="repo.state-system",
            observed_at="2026-05-01T17:31:00Z",
            candidate_state_refs=["state.repo.state-system.runtime"],
            governance_refs=["governance.source-of-truth-discipline"],
        )

        self.assertEqual("source.git.repo.state-system.abc123def456", event["id"])
        self.assertEqual("git", event["source_system"])
        self.assertEqual("commit.created", event["source_event"])
        self.assertEqual("git:repo.state-system:commit:abc123def456", event["source_refs"][0])
        self.assertEqual("repo.state-system", event["change"]["object_ref"])
        self.assertEqual("commit", event["change"]["field"])
        self.assertEqual("abc123def456", event["change"]["new_value"]["sha"])
        self.assertEqual(
            ["state_system/cli.py", "state_system/runtime.py"],
            event["change"]["new_value"]["changed_files"],
        )
        self.assertEqual(
            "git:repo.state-system:commit:abc123def456",
            event["idempotency"]["key"],
        )
        self.assertEqual(
            [],
            validate_schema(
                event,
                load_json(ROOT / "schemas" / "source-event.schema.json"),
            ),
        )

    def test_cli_git_commit_event_can_be_ingested_by_trigger_runtime(self):
        with TemporaryDirectory() as directory:
            commit_path = Path(directory) / "commit.json"
            commit_path.write_text(
                json.dumps(
                    {
                        "sha": "fedcba654321",
                        "author_name": "Braydon McConnell",
                        "author_email": "user@example.com",
                        "authored_at": "2026-05-01T18:00:00Z",
                        "subject": "docs: update runtime v0",
                        "body": "",
                        "changed_files": ["docs/concepts/runtime-v0.md"],
                    }
                ),
                encoding="utf-8",
            )
            output = StringIO()

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "git-commit-event",
                    str(commit_path),
                    "--repo-ref",
                    "repo.state-system",
                    "--observed-at",
                    "2026-05-01T18:01:00Z",
                    "--candidate-state-ref",
                    "state.repo.state-system.runtime",
                    "--governance-ref",
                    "governance.source-of-truth-discipline",
                    "--ingest",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            stores = StateStoreBundle(Path(directory))
            self.assertEqual(0, code)
            self.assertTrue(payload["ingested"]["created"])
            self.assertEqual(
                "trigger.git.repo.state-system.fedcba654321",
                payload["ingested"]["trigger"]["id"],
            )
            self.assertEqual(
                ["source.git.repo.state-system.fedcba654321"],
                stores.source_events.list_ids(),
            )


if __name__ == "__main__":
    unittest.main()
