import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ModuleEntrypointTests(unittest.TestCase):
    """Tests for the primary simulink_cli entrypoint and backward-compat wrappers."""

    def _run_schema(self, module):
        command = [sys.executable, "-m", module, "schema"]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return completed

    def test_simulink_cli_entrypoint_schema(self):
        completed = self._run_schema("simulink_cli")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("actions", payload)
        self.assertIn("schema", payload["actions"])
        self.assertIn("scan", payload["actions"])
        self.assertIn("set_param", payload["actions"])
        self.assertEqual(payload["version"], "2.0")

    def test_backward_compat_scan_entrypoint(self):
        completed = self._run_schema("skills.simulink_scan")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("actions", payload)

    def test_backward_compat_edit_entrypoint(self):
        completed = self._run_schema("skills.simulink_edit")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("actions", payload)
        self.assertIn("set_param", payload["actions"])


if __name__ == "__main__":
    unittest.main()
