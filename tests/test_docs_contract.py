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

    def test_readme_mentions_schema_and_output_controls(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("simulink_cli schema", text)
        self.assertIn("--max-blocks", text)
        self.assertIn("--max-params", text)
        self.assertIn("--max-edges", text)
        self.assertIn('{"action":"connections"', text)
        self.assertIn("structured metadata", text)

    def test_readme_documents_matlab_prerequisites(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("MATLAB Engine for Python", text)
        self.assertIn("matlab.engine.shareEngine", text)

    def test_skill_and_reference_include_engine_unavailable_route(self):
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        reference_text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("engine_unavailable", skill_text)
        self.assertIn("engine_unavailable", reference_text)

    def test_skill_documents_highlight_as_readonly_visual_action(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("Visual location in Simulink -> `highlight`", text)
        self.assertIn("`hilite_system`", text)

    def test_reference_includes_highlight_action_examples(self):
        text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("## Highlight Action", text)
        self.assertIn("simulink_cli highlight", text)

    def test_skill_and_reference_document_connections_action(self):
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        reference_text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("connections", skill_text)
        self.assertIn("## Connections Action", reference_text)
        self.assertIn("simulink_cli connections", reference_text)
        self.assertIn("--max-edges", reference_text)
        self.assertIn("--fields", reference_text)

    def test_readme_mentions_connections_action(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("`connections`", text)

    def test_scenarios_include_recovery_chain_examples(self):
        text = SCENARIOS_PATH.read_text(encoding="utf-8")
        required_tokens = [
            "session_required",
            "model_required",
            "subsystem_not_found",
            "inactive_parameter",
            "highlight",
            "connections",
        ]
        for token in required_tokens:
            self.assertIn(token, text)

    def test_skill_and_reference_document_find_action(self):
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        reference_text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("find", skill_text.lower())
        self.assertIn("Find", reference_text)

    def test_readme_mentions_find_action(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("`find`", text)

    def test_scenarios_include_find_examples(self):
        text = SCENARIOS_PATH.read_text(encoding="utf-8")
        self.assertIn("find", text)


if __name__ == "__main__":
    unittest.main()
