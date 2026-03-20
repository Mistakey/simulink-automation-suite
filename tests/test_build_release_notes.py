import io
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_release_notes import (
    ReleaseNotesError,
    build_release_notes,
    find_release_document,
    main as build_release_notes_main,
)


class BuildReleaseNotesTests(unittest.TestCase):
    def test_find_release_document_matches_versioned_release_doc(self):
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            release_doc = repo_root / "docs" / "release" / "2026-03-20-v2.0.1.md"
            release_doc.parent.mkdir(parents=True)
            release_doc.write_text("# Release v2.0.1\n", encoding="utf-8")

            matched = find_release_document(repo_root, "2.0.1")

            self.assertEqual(matched, release_doc)

    def test_find_release_document_rejects_ambiguous_matches(self):
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            release_dir = repo_root / "docs" / "release"
            release_dir.mkdir(parents=True)
            release_dir.joinpath("2026-03-20-v2.0.1.md").write_text("# One\n", encoding="utf-8")
            release_dir.joinpath("release-v2.0.1.md").write_text("# Two\n", encoding="utf-8")

            with self.assertRaises(ReleaseNotesError) as ctx:
                find_release_document(repo_root, "2.0.1")

            self.assertIn("multiple", str(ctx.exception).lower())
            self.assertIn("v2.0.1", str(ctx.exception))

    def test_build_release_notes_falls_back_to_git_history(self):
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            self._init_git_repo(repo_root)
            self._commit(repo_root, "docs: initial")
            self._run_git(repo_root, "tag", "v1.0.0")
            self._commit(repo_root, "feat: add auto release")
            self._commit(repo_root, "docs: add release checklist")

            result = build_release_notes(repo_root, version="1.0.1", tag="v1.0.1", ref="HEAD")

            self.assertEqual(result.source_kind, "generated")
            self.assertEqual(result.previous_tag, "v1.0.0")
            self.assertIn("# Release v1.0.1", result.body)
            self.assertIn("## Summary", result.body)
            self.assertIn("## Highlights", result.body)
            self.assertIn("## Compatibility / Upgrade Notes", result.body)
            self.assertIn("## Validation", result.body)
            self.assertIn("feat: add auto release", result.body)
            self.assertIn("docs: add release checklist", result.body)

    def test_main_keeps_stdout_as_pure_markdown_without_output_flag(self):
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            release_doc = repo_root / "docs" / "release" / "2026-03-20-v2.0.1.md"
            release_doc.parent.mkdir(parents=True)
            release_doc.write_text("# Release v2.0.1\n", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = build_release_notes_main(
                    ["--repo-root", str(repo_root), "--tag", "v2.0.1"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "# Release v2.0.1\n")
            self.assertIn("source=document:", stderr.getvalue())

    def _init_git_repo(self, repo_root: Path) -> None:
        self._run_git(repo_root, "init")
        self._run_git(repo_root, "config", "user.name", "Codex Test")
        self._run_git(repo_root, "config", "user.email", "codex@example.com")

    def _commit(self, repo_root: Path, message: str) -> None:
        marker = repo_root / "marker.txt"
        existing = marker.read_text(encoding="utf-8") if marker.exists() else ""
        marker.write_text(existing + message + "\n", encoding="utf-8")
        self._run_git(repo_root, "add", "marker.txt")
        self._run_git(repo_root, "commit", "-m", message)

    def _run_git(self, repo_root: Path, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    unittest.main()
