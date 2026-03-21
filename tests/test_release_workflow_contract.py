import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"
CLAUDE_PATH = REPO_ROOT / ".claude" / "CLAUDE.md"
RELEASE_SKILL_PATH = REPO_ROOT / ".claude" / "skills" / "release" / "SKILL.md"
AGENT_FIRST_RULE_PATH = REPO_ROOT / ".claude" / "rules" / "agent-first-cli.md"
CHECKLIST_PATH = REPO_ROOT / "docs" / "release" / "2026-03-07-github-marketplace-release-checklist.md"
CODEX_INSTRUCTIONS_PATH = REPO_ROOT / ".codex" / "instructions.md"
RELEASE_TEMPLATE_PATH = REPO_ROOT / "docs" / "release" / "bilingual-template.md"


class ReleaseWorkflowContractTests(unittest.TestCase):
    def test_release_workflow_exists_with_tag_and_dispatch_triggers(self):
        self.assertTrue(WORKFLOW_PATH.exists(), "release workflow is missing")
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("push:", text)
        self.assertIn("v*.*.*", text)
        self.assertIn("contents: write", text)

    def test_release_workflow_runs_validation_notes_and_release_steps(self):
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("scripts/check_release_metadata.py", text)
        self.assertIn("scripts/build_release_notes.py", text)
        self.assertIn("claude plugin validate .", text)
        self.assertIn("tests.test_plugin_manifest_contract", text)
        self.assertIn("gh release create", text)
        self.assertIn("gh release edit", text)
        self.assertIn("checkout_ref", text)
        self.assertIn("github.sha", text)
        self.assertIn("--ref \"${{ steps.release_context.outputs.release_ref }}\"", text)

    def test_release_docs_explain_tag_driven_automation(self):
        claude_text = CLAUDE_PATH.read_text(encoding="utf-8")
        release_skill_text = RELEASE_SKILL_PATH.read_text(encoding="utf-8")
        agent_first_text = AGENT_FIRST_RULE_PATH.read_text(encoding="utf-8")
        checklist_text = CHECKLIST_PATH.read_text(encoding="utf-8")
        codex_text = CODEX_INSTRUCTIONS_PATH.read_text(encoding="utf-8")

        self.assertIn("release.yml", claude_text)
        self.assertIn("release", claude_text.lower())
        self.assertNotIn("## Release Automation", claude_text)
        self.assertNotIn("Release notes source priority", claude_text)
        self.assertNotIn("check_release_metadata.py --tag", claude_text)
        self.assertIn("tag-driven", release_skill_text.lower())
        self.assertIn("workflow_dispatch", release_skill_text)
        self.assertIn("build_release_notes.py", release_skill_text)
        self.assertIn("docs/release", release_skill_text)
        self.assertIn("fallback", release_skill_text.lower())
        self.assertIn("schema", agent_first_text.lower())
        self.assertIn("major.minor", agent_first_text)
        self.assertIn("workflow_dispatch", checklist_text)
        self.assertIn("auto release", checklist_text.lower())
        self.assertIn("docs/release", checklist_text)
        self.assertIn("Subagent delegation is allowed", codex_text)
        self.assertIn(".github/workflows/release.yml", codex_text)
        self.assertIn("scripts/check_release_metadata.py", codex_text)

    def test_curated_release_doc_guidance_supports_bilingual_notes(self):
        release_skill_text = RELEASE_SKILL_PATH.read_text(encoding="utf-8")
        checklist_text = CHECKLIST_PATH.read_text(encoding="utf-8")

        self.assertTrue(RELEASE_TEMPLATE_PATH.exists(), "bilingual release template is missing")

        template_text = RELEASE_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("bilingual", release_skill_text.lower())
        self.assertIn("中文", release_skill_text)
        self.assertIn("bilingual", checklist_text.lower())
        self.assertIn("中文", checklist_text)
        self.assertIn("## 中文说明", template_text)
        self.assertIn("docs/release/zh-CN/", template_text)


if __name__ == "__main__":
    unittest.main()
