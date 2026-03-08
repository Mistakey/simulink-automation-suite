import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_MANIFEST_PATH = REPO_ROOT / ".claude-plugin" / "plugin.json"


class MarketplaceManifestContractTests(unittest.TestCase):
    def test_marketplace_file_exists(self):
        self.assertTrue(MARKETPLACE_PATH.exists())

    def test_marketplace_has_required_top_level_fields(self):
        data = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data.get("name"), "simulink-automation-marketplace")
        self.assertIn("owner", data)
        self.assertIsInstance(data["owner"], dict)
        self.assertEqual(data["owner"].get("name"), "kelch")
        self.assertIn("plugins", data)
        self.assertIsInstance(data["plugins"], list)
        self.assertGreaterEqual(len(data["plugins"]), 1)

    def test_marketplace_registers_current_plugin_from_repo_root(self):
        data = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
        plugin_manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        plugin_name = plugin_manifest.get("name")

        matched = [
            item
            for item in data.get("plugins", [])
            if isinstance(item, dict) and item.get("name") == plugin_name
        ]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].get("source"), "./")

    def test_marketplace_plugin_version_matches_plugin_manifest(self):
        data = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
        plugin_manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        plugin_name = plugin_manifest.get("name")
        plugin_version = plugin_manifest.get("version")

        matched = [
            item
            for item in data.get("plugins", [])
            if isinstance(item, dict) and item.get("name") == plugin_name
        ]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].get("version"), plugin_version)


if __name__ == "__main__":
    unittest.main()
