import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "simulink_scan" / "SKILL.md"
REFERENCE_PATH = REPO_ROOT / "skills" / "simulink_scan" / "reference.md"
README_PATH = REPO_ROOT / "README.md"
README_ZH_PATH = REPO_ROOT / "README.zh-CN.md"
CLAUDE_PATH = REPO_ROOT / ".claude" / "CLAUDE.md"


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

    def test_readme_distinguishes_unknown_parameter_and_param_not_found(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("unknown_parameter", text)
        self.assertIn("param_not_found", text)
        self.assertIn("request field or flag", text)
        self.assertIn("runtime parameter", text)

    def test_readme_recommends_json_mode_for_complex_strings_and_newlines(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("canonical contract surface for complex strings and newlines", text)
        self.assertIn("--json", text)
        self.assertIn("inspect", text)

    def test_readme_documents_clean_stdout_contract(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("single machine-readable JSON payload", text)
        self.assertIn("stderr", text)

    def test_readme_documents_matlab_prerequisites(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("MATLAB Engine for Python", text)
        self.assertIn("matlab.engine.shareEngine", text)

    def test_readme_mentions_session_state_error_codes(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("state_write_failed", text)
        self.assertIn("state_clear_failed", text)

    def test_readme_documents_guarded_edit_loop(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("apply_payload", text)
        self.assertIn("precondition_failed", text)
        self.assertIn("verification_failed", text)
        self.assertIn("expected_current_value", text)

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

    def test_skill_and_reference_document_find_action(self):
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        reference_text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("find", skill_text.lower())
        self.assertIn("Find", reference_text)

    def test_readme_mentions_find_action(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("`find`", text)

    def test_readme_zh_matches_error_and_json_contract(self):
        text = README_ZH_PATH.read_text(encoding="utf-8")
        self.assertIn("unknown_parameter", text)
        self.assertIn("param_not_found", text)
        self.assertIn("复杂字符串", text)
        self.assertIn("换行", text)
        self.assertIn("stdout", text)

    def test_readme_zh_documents_guarded_edit_loop(self):
        text = README_ZH_PATH.read_text(encoding="utf-8")
        self.assertIn("apply_payload", text)
        self.assertIn("precondition_failed", text)
        self.assertIn("verification_failed", text)
        self.assertIn("expected_current_value", text)

    def test_claude_md_separates_unit_tests_from_live_matlab_verification(self):
        text = CLAUDE_PATH.read_text(encoding="utf-8")
        self.assertIn("live MATLAB smoke verification", text)
        self.assertIn("unit tests", text)
        self.assertIn("not sufficient", text)


if __name__ == "__main__":
    unittest.main()
