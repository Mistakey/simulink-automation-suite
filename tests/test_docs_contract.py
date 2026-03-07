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


if __name__ == "__main__":
    unittest.main()
