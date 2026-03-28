import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "simulink_automation"
SKILL_PATH = SKILL_DIR / "SKILL.md"
REFERENCE_PATH = SKILL_DIR / "reference.md"
README_PATH = REPO_ROOT / "README.md"
README_ZH_PATH = REPO_ROOT / "README.zh-CN.md"
CLAUDE_PATH = REPO_ROOT / ".claude" / "CLAUDE.md"
PLUGIN_MANIFEST_PATH = REPO_ROOT / ".claude-plugin" / "plugin.json"


class DocsContractTests(unittest.TestCase):
    # -- Skill structure -------------------------------------------------------

    def test_skill_has_playbook_sections(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        required_sections = [
            "## Prerequisites",
            "## Discovery",
            "## Workflow Strategy",
            "## Write Safety Model",
            "## Recovery Routing",
            "## Output Discipline",
        ]
        for section in required_sections:
            self.assertIn(section, text)

    def test_skill_has_frontmatter(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"))
        self.assertIn("name: simulink-automation", text)

    def test_skill_references_schema_for_discovery(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("schema", text)
        self.assertIn("authoritative reference", text.lower())

    def test_skill_documents_write_safety_model(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("dry_run", text)
        self.assertIn("apply_payload", text)
        self.assertIn("rollback", text)
        self.assertIn("precondition_failed", text)
        self.assertIn("verification_failed", text)

    def test_skill_recovery_routing_covers_key_errors(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        required_codes = [
            "engine_unavailable",
            "no_session",
            "session_required",
            "session_not_found",
            "model_required",
            "block_not_found",
            "param_not_found",
            "precondition_failed",
            "set_param_failed",
            "verification_failed",
            "model_already_loaded",
            "invalid_json",
            "source_not_found",
            "block_already_exists",
            "model_dirty",
            "line_already_exists",
            "line_not_found",
            "simulation_failed",
            "update_failed",
            "eval_failed",
            "eval_timeout",
        ]
        for code in required_codes:
            self.assertIn(code, text, f"Recovery routing missing: {code}")

    # -- Reference (response shapes) -------------------------------------------

    def test_reference_exists(self):
        self.assertTrue(REFERENCE_PATH.exists())

    def test_reference_documents_set_param_response_shapes(self):
        text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("apply_payload", text)
        self.assertIn("expected_current_value", text)
        self.assertIn("precondition_failed", text)
        self.assertIn("write_state", text)
        self.assertIn("verified", text)

    def test_reference_documents_failure_semantics(self):
        text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("Failure Semantics", text)
        self.assertIn("safe_to_retry", text)
        self.assertIn("recommended_recovery", text)

    def test_reference_documents_value_type_notes(self):
        text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("%.3f", text)
        self.assertIn("Value Type Notes", text)

    # -- README ----------------------------------------------------------------

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

    def test_readme_mentions_connections_action(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("`connections`", text)

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

    # -- CLAUDE.md -------------------------------------------------------------

    def test_claude_md_separates_unit_tests_from_live_matlab_verification(self):
        text = CLAUDE_PATH.read_text(encoding="utf-8")
        self.assertIn("live MATLAB smoke verification", text)
        self.assertIn("unit tests", text)
        self.assertIn("not sufficient", text)


    # -- Handoff contract -------------------------------------------------

    def _get_handoff_text(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        handoff_start = text.index("## Responsibility & Handoff")
        next_h2 = text.find("\n## ", handoff_start + 1)
        return text[handoff_start:next_h2] if next_h2 != -1 else text[handoff_start:]

    def test_skill_has_handoff_section(self):
        text = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("## Responsibility & Handoff", text)

    def test_handoff_declares_direct_handling_bucket(self):
        self.assertIn("Direct", self._get_handoff_text())

    def test_handoff_direct_bucket_covers_required_actions(self):
        handoff_text = self._get_handoff_text()
        for action in ["session", "list_opened", "schema", "highlight"]:
            self.assertIn(action, handoff_text, f"Direct bucket missing: {action}")
        self.assertIn("inspect", handoff_text)

    def test_handoff_declares_delegation_bucket(self):
        self.assertIn("Delegate", self._get_handoff_text())

    def test_handoff_delegation_bucket_covers_required_actions(self):
        handoff_text = self._get_handoff_text()
        for action in ["scan", "find", "connections"]:
            self.assertIn(action, handoff_text, f"Delegation bucket missing: {action}")
        self.assertIn("multi-step", handoff_text.lower())

    def test_handoff_direct_bucket_covers_v2_4_actions(self):
        handoff_text = self._get_handoff_text()
        for action in ["model_close", "model_update", "line_add"]:
            self.assertIn(action, handoff_text, f"Direct bucket missing: {action}")

    def test_handoff_direct_bucket_covers_v2_5_actions(self):
        handoff_text = self._get_handoff_text()
        for action in ["line_delete", "block_delete", "simulate"]:
            self.assertIn(action, handoff_text, f"Direct bucket missing: {action}")

    def test_handoff_direct_bucket_covers_v2_6_actions(self):
        handoff_text = self._get_handoff_text()
        for action in ["matlab_eval"]:
            self.assertIn(action, handoff_text, f"Direct bucket missing: {action}")

    def test_handoff_declares_composite_request_rule(self):
        self.assertIn("composite", self._get_handoff_text().lower())

    # -- README agent coverage (manifest-driven) --------------------------

    def _get_published_agent_names(self):
        """Read agent names from manifest-declared agent files' frontmatter."""
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        names = []
        for entry in manifest.get("agents", []):
            path = REPO_ROOT / entry.lstrip("./")
            text = path.read_text(encoding="utf-8")
            match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
            if match:
                names.append(match.group(1).strip())
        return names

    def test_readme_mentions_each_published_agent(self):
        text = README_PATH.read_text(encoding="utf-8")
        for name in self._get_published_agent_names():
            self.assertIn(name, text, f"README.md missing agent: {name}")

    def test_readme_zh_mentions_each_published_agent(self):
        text = README_ZH_PATH.read_text(encoding="utf-8")
        for name in self._get_published_agent_names():
            self.assertIn(name, text, f"README.zh-CN.md missing agent: {name}")


if __name__ == "__main__":
    unittest.main()
