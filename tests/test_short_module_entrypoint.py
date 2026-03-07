import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ShortModuleEntrypointTests(unittest.TestCase):
    def test_module_entrypoint_supports_schema_action(self):
        command = [sys.executable, "-m", "skills.simulink_scan", "schema"]
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


if __name__ == "__main__":
    unittest.main()
