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


if __name__ == "__main__":
    unittest.main()
