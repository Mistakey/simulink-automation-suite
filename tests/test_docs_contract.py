import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "simulink_scan" / "SKILL.md"
REFERENCE_PATH = REPO_ROOT / "skills" / "simulink_scan" / "reference.md"
README_PATH = REPO_ROOT / "README.md"
SCENARIOS_PATH = REPO_ROOT / "skills" / "simulink_scan" / "test-scenarios.md"


class DocsContractTests(unittest.TestCase):
    def test_skill_has_agent_first_sections(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        required_sections = [
            "## Preflight",
            "## Action Selection",
            "## Execution Templates",
            "## Recovery Routing",
        ]
        for section in required_sections:
            self.assertIn(section, text)

    def test_reference_has_recovery_matrix_for_key_errors(self):
        text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("## Recovery Matrix", text)
        required_codes = [
            "session_required",
            "session_not_found",
            "model_required",
            "inactive_parameter",
            "invalid_json",
        ]
        for code in required_codes:
            self.assertIn(f"`{code}`", text)


if __name__ == "__main__":
    unittest.main()
