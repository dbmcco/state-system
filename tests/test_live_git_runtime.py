from io import StringIO
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.source_adapters import git_commit_metadata_from_repo
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class LiveGitRuntimeTests(unittest.TestCase):
    def test_seed_runtime_creates_repo_state_for_live_trial(self):
        with TemporaryDirectory() as directory:
            output = StringIO()

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "seed-runtime",
                    "--repo-ref",
                    "repo.state-system",
                    "--created-at",
                    "2026-05-01T18:30:00Z",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            stores = StateStoreBundle(Path(directory))
            self.assertEqual(0, code)
            self.assertEqual(
                ["state.repo.state-system.runtime"],
                payload["created_state_object_refs"],
            )
            self.assertEqual(
                "state.repo.state-system.runtime",
                stores.state_objects.read("state.repo.state-system.runtime")["id"],
            )

    def test_git_commit_from_repo_can_ingest_real_commit_without_metadata_file(self):
        with TemporaryDirectory() as repo_directory, TemporaryDirectory() as state_directory:
            repo = Path(repo_directory)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Runtime Tester")
            _git(repo, "config", "user.email", "runtime@example.com")
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            _git(repo, "add", "README.md")
            _git(repo, "commit", "-m", "feat: create live fixture")
            sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    state_directory,
                    "git-commit-from-repo",
                    str(repo),
                    "--commit",
                    "HEAD",
                    "--repo-ref",
                    "repo.live-fixture",
                    "--observed-at",
                    "2026-05-01T18:35:00Z",
                    "--candidate-state-ref",
                    "state.repo.live-fixture.runtime",
                    "--ingest",
                ],
                stdout=output,
            )

            payload = json.loads(output.getvalue())
            stores = StateStoreBundle(Path(state_directory))
            self.assertEqual(0, code)
            self.assertEqual(sha, payload["source_event"]["change"]["new_value"]["sha"])
            self.assertEqual(["README.md"], payload["source_event"]["change"]["new_value"]["changed_files"])
            self.assertTrue(payload["ingested"]["created"])
            self.assertEqual(
                [f"source.git.repo.live-fixture.{sha}"],
                stores.source_events.list_ids(),
            )

    def test_source_recent_index_builds_alex_and_maya_packages_from_routes(self):
        with TemporaryDirectory() as repo_directory, TemporaryDirectory() as state_directory:
            repo = Path(repo_directory)
            state_root = Path(state_directory)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Runtime Tester")
            _git(repo, "config", "user.email", "runtime@example.com")
            (repo / "state_system").mkdir()
            (repo / "state_system" / "source_adapters.py").write_text(
                "adapter\n",
                encoding="utf-8",
            )
            _git(repo, "add", "state_system/source_adapters.py")
            _git(repo, "commit", "-m", "feat: add source adapter")
            sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

            self._run_cli(
                state_directory,
                [
                    "seed-runtime",
                    "--repo-ref",
                    "repo.live-fixture",
                    "--created-at",
                    "2026-05-01T18:40:00Z",
                ],
            )
            self._run_cli(
                state_directory,
                [
                    "git-commit-from-repo",
                    str(repo),
                    "--commit",
                    "HEAD",
                    "--repo-ref",
                    "repo.live-fixture",
                    "--observed-at",
                    "2026-05-01T18:41:00Z",
                    "--candidate-state-ref",
                    "state.repo.live-fixture.runtime",
                    "--ingest",
                ],
            )
            routes_path = state_root / "routes.json"
            routes_path.write_text(
                json.dumps(
                    [
                        {
                            "persona_ref": "persona.alex",
                            "relevance_tier": "primary",
                            "routing_reason": (
                                "Source adapter code affects runtime operations."
                            ),
                            "included": True,
                        },
                        {
                            "persona_ref": "persona.maya",
                            "relevance_tier": "excluded",
                            "routing_reason": (
                                "Internal adapter plumbing is not market-facing."
                            ),
                            "included": False,
                            "excluded_context_summary": (
                                "No market-facing capability claim is present."
                            ),
                        },
                    ]
                ),
                encoding="utf-8",
            )

            recent = self._run_cli(
                state_directory,
                [
                    "index-source-recent",
                    f"source.git.repo.live-fixture.{sha}",
                    "--created-at",
                    "2026-05-01T18:42:00Z",
                    "--summary",
                    "Git commit added source adapter code.",
                    "--routes",
                    str(routes_path),
                    "--opportunity-class-hint",
                    "runtime_change",
                    "--watermark-ref",
                    f"git:repo.live-fixture:commit:{sha}",
                    "--stale-after",
                    "2026-05-02T18:42:00Z",
                ],
            )
            alex_package = self._run_cli(
                state_directory,
                [
                    "build-package",
                    str(ROOT / "examples" / "alex-persona.json"),
                    "context.alex.live-git",
                    "--created-at",
                    "2026-05-01T18:43:00Z",
                    "--review-goal",
                    "Review Alex-relevant live Git changes.",
                    "--valid-until",
                    "2026-05-02T18:43:00Z",
                ],
            )
            maya_package = self._run_cli(
                state_directory,
                [
                    "build-package",
                    str(ROOT / "examples" / "maya-persona.json"),
                    "context.maya.live-git",
                    "--created-at",
                    "2026-05-01T18:43:00Z",
                    "--review-goal",
                    "Review Maya-relevant live Git changes.",
                    "--valid-until",
                    "2026-05-02T18:43:00Z",
                ],
            )

            self.assertEqual(f"recent.git.repo.live-fixture.{sha}", recent["id"])
            self.assertEqual(
                [f"recent.git.repo.live-fixture.{sha}"],
                [
                    entry["id"]
                    for entry in alex_package["recent_change_context"]["entries"]
                ],
            )
            self.assertEqual([], maya_package["recent_change_context"]["entries"])
            self.assertEqual(
                [f"recent.git.repo.live-fixture.{sha}"],
                [
                    item["recent_change_ref"]
                    for item in maya_package["excluded_context_summary"]
                ],
            )

    def test_git_commit_metadata_from_repo_reads_subject_author_and_files(self):
        with TemporaryDirectory() as repo_directory:
            repo = Path(repo_directory)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Runtime Tester")
            _git(repo, "config", "user.email", "runtime@example.com")
            (repo / "a.txt").write_text("a\n", encoding="utf-8")
            (repo / "b.txt").write_text("b\n", encoding="utf-8")
            _git(repo, "add", "a.txt", "b.txt")
            _git(repo, "commit", "-m", "docs: capture files")

            metadata = git_commit_metadata_from_repo(repo, "HEAD")

            self.assertEqual("Runtime Tester", metadata["author_name"])
            self.assertEqual("runtime@example.com", metadata["author_email"])
            self.assertEqual("docs: capture files", metadata["subject"])
            self.assertEqual(["a.txt", "b.txt"], metadata["changed_files"])

    def _run_cli(self, state_directory: str, args: list[str]):
        output = StringIO()
        code = cli.main(
            [
                "--project-root",
                str(ROOT),
                "--state-root",
                state_directory,
                *args,
            ],
            stdout=output,
        )
        self.assertEqual(0, code, output.getvalue())
        return json.loads(output.getvalue())


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


if __name__ == "__main__":
    unittest.main()
