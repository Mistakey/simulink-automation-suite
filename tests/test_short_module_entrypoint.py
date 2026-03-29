import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ModuleEntrypointTests(unittest.TestCase):
    """Tests for the primary simulink_cli entrypoint."""

    def test_simulink_cli_entrypoint_schema(self):
        command = [sys.executable, "-m", "simulink_cli", "schema"]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("actions", payload)
        self.assertIn("schema", payload["actions"])
        self.assertIn("scan", payload["actions"])
        self.assertIn("set_param", payload["actions"])
        self.assertEqual(payload["version"], "2.6")


if __name__ == "__main__":
    unittest.main()
