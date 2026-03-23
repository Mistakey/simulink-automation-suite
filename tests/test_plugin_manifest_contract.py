import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST_PATH = REPO_ROOT / ".claude-plugin" / "plugin.json"


class PluginManifestContractTests(unittest.TestCase):
    def test_manifest_positions_plugin_as_suite(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("name"), "simulink-automation-suite")
        self.assertIn("suite", manifest.get("description", "").lower())

    def test_manifest_declares_skills_directory(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertIn("skills", manifest)
        self.assertIsInstance(manifest["skills"], list)
        self.assertIn("./skills/", manifest["skills"])

    def test_manifest_does_not_declare_default_hooks_file(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("hooks", manifest)

    def test_manifest_keywords_include_edit_without_future_placeholder(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        keywords = manifest.get("keywords", [])
        self.assertIn("edit", keywords)
        self.assertNotIn("future-editing", keywords)

    def test_manifest_declares_agents_field(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertIn("agents", manifest)

    def test_manifest_agents_is_nonempty_list(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        agents = manifest.get("agents", [])
        self.assertIsInstance(agents, list)
        self.assertGreater(len(agents), 0)

    def test_manifest_agent_entries_are_md_paths(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        for entry in manifest.get("agents", []):
            self.assertIsInstance(entry, str)
            self.assertTrue(entry.endswith(".md"), f"Agent entry must be .md path: {entry}")

    def test_manifest_declared_agent_files_exist(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        for entry in manifest.get("agents", []):
            agent_path = REPO_ROOT / entry.lstrip("./")
            self.assertTrue(agent_path.exists(), f"Declared agent file missing: {entry}")


if __name__ == "__main__":
    unittest.main()
