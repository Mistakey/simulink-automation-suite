import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EDIT_SKILL_DIR = REPO_ROOT / "skills" / "simulink_edit"


class EditDocsContractTests(unittest.TestCase):
    def test_skill_md_exists(self):
        self.assertTrue((EDIT_SKILL_DIR / "SKILL.md").exists())

    def test_reference_md_exists(self):
        self.assertTrue((EDIT_SKILL_DIR / "reference.md").exists())

    def test_test_scenarios_md_exists(self):
        self.assertTrue((EDIT_SKILL_DIR / "test-scenarios.md").exists())

    def test_skill_md_contains_set_param(self):
        text = (EDIT_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("set_param", text)

    def test_skill_md_contains_dry_run(self):
        text = (EDIT_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("dry_run", text)

    def test_skill_md_contains_rollback(self):
        text = (EDIT_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("rollback", text)

    def test_skill_md_contains_safety_model(self):
        text = (EDIT_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Safety Model", text)
        self.assertIn("verification_failed", text)

    def test_reference_md_contains_recovery_matrix(self):
        text = (EDIT_SKILL_DIR / "reference.md").read_text(encoding="utf-8")
        self.assertIn("Recovery Matrix", text)

    def test_reference_md_contains_param_not_found(self):
        text = (EDIT_SKILL_DIR / "reference.md").read_text(encoding="utf-8")
        self.assertIn("param_not_found", text)

    def test_reference_md_contains_set_param_failed(self):
        text = (EDIT_SKILL_DIR / "reference.md").read_text(encoding="utf-8")
        self.assertIn("set_param_failed", text)

    def test_reference_md_documents_literal_percent_value_examples(self):
        text = (EDIT_SKILL_DIR / "reference.md").read_text(encoding="utf-8")
        self.assertIn("%.3f", text)

    def test_reference_md_documents_write_state_and_rollback_failure(self):
        text = (EDIT_SKILL_DIR / "reference.md").read_text(encoding="utf-8")
        self.assertIn("verification_failed", text)
        self.assertIn("write_state", text)
        self.assertIn("details.rollback", text)

    def test_skill_md_has_frontmatter(self):
        text = (EDIT_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"))
        self.assertIn("name: simulink-edit", text)

    def test_test_scenarios_contains_set_param(self):
        text = (EDIT_SKILL_DIR / "test-scenarios.md").read_text(encoding="utf-8")
        self.assertIn("set_param", text)
        self.assertIn("verification_failed", text)
        self.assertIn("newline", text)


if __name__ == "__main__":
    unittest.main()
