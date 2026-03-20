import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_release_metadata import (
    ReleaseMetadataError,
    extract_schema_version,
    validate_release_metadata,
)


class ReleaseMetadataTests(unittest.TestCase):
    def test_extract_schema_version_reads_literal_from_build_schema_payload(self):
        with TemporaryDirectory() as tmpdir:
            core_path = Path(tmpdir) / "core.py"
            core_path.write_text(
                textwrap.dedent(
                    """
                    def build_schema_payload():
                        return {
                            "version": "2.4",
                            "actions": {},
                        }
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(extract_schema_version(core_path), "2.4")

    def test_validate_release_metadata_accepts_synced_versions_and_tag(self):
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            self._write_repo_files(repo_root, plugin_version="2.3.4", marketplace_version="2.3.4", schema_version="2.3")

            metadata = validate_release_metadata(repo_root, expected_tag="v2.3.4")

            self.assertEqual(metadata.plugin_version, "2.3.4")
            self.assertEqual(metadata.marketplace_version, "2.3.4")
            self.assertEqual(metadata.schema_version, "2.3")

    def test_validate_release_metadata_rejects_schema_version_mismatch(self):
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            self._write_repo_files(repo_root, plugin_version="2.3.4", marketplace_version="2.3.4", schema_version="2.2")

            with self.assertRaises(ReleaseMetadataError) as ctx:
                validate_release_metadata(repo_root, expected_tag="v2.3.4")

            self.assertIn("schema", str(ctx.exception).lower())
            self.assertIn("2.3", str(ctx.exception))

    def test_validate_release_metadata_rejects_tag_mismatch(self):
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            self._write_repo_files(repo_root, plugin_version="2.3.4", marketplace_version="2.3.4", schema_version="2.3")

            with self.assertRaises(ReleaseMetadataError) as ctx:
                validate_release_metadata(repo_root, expected_tag="v2.3.5")

            self.assertIn("tag", str(ctx.exception).lower())
            self.assertIn("2.3.4", str(ctx.exception))

    def _write_repo_files(
        self,
        repo_root: Path,
        *,
        plugin_version: str,
        marketplace_version: str,
        schema_version: str,
    ) -> None:
        plugin_dir = repo_root / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        plugin_dir.joinpath("plugin.json").write_text(
            textwrap.dedent(
                f"""
                {{
                  "name": "simulink-automation-suite",
                  "version": "{plugin_version}",
                  "skills": ["./skills/"]
                }}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        plugin_dir.joinpath("marketplace.json").write_text(
            textwrap.dedent(
                f"""
                {{
                  "name": "simulink-automation-marketplace",
                  "plugins": [
                    {{
                      "name": "simulink-automation-suite",
                      "source": "./",
                      "version": "{marketplace_version}"
                    }}
                  ]
                }}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        core_dir = repo_root / "simulink_cli"
        core_dir.mkdir(parents=True)
        core_dir.joinpath("core.py").write_text(
            textwrap.dedent(
                f"""
                def build_schema_payload():
                    return {{
                        "version": "{schema_version}",
                        "actions": {{}},
                    }}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
