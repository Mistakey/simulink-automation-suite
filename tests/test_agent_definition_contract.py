import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST_PATH = REPO_ROOT / ".claude-plugin" / "plugin.json"

CANONICAL_ENVELOPE_SECTIONS = [
    "Context",
    "Answer",
    "Evidence",
    "Actions Performed",
    "Limitations",
    "Suggested Followup",
]


def _load_declared_agents():
    """Return list of (relative_path, resolved_path) for each declared agent."""
    manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
    agents = manifest.get("agents", [])
    result = []
    for entry in agents:
        clean = entry.lstrip("./")
        resolved = REPO_ROOT / clean
        result.append((entry, resolved))
    return result


def _parse_frontmatter(text):
    """Extract YAML frontmatter from markdown text (stdlib only, no PyYAML)."""
    if not text.startswith("---"):
        return {}
    end = text.index("---", 3)
    raw = text[3:end].strip()
    result = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _extract_h2_headings(text):
    """Extract ordered list of H2 heading texts from markdown body (after frontmatter)."""
    body = text
    if text.startswith("---"):
        end = text.index("---", 3)
        body = text[end + 3 :]
    return re.findall(r"^## (.+)$", body, re.MULTILINE)


class AgentDefinitionContractTests(unittest.TestCase):
    def test_manifest_agents_not_empty(self):
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        agents = manifest.get("agents", [])
        self.assertGreater(len(agents), 0, "plugin.json agents array must not be empty")

    def test_each_declared_agent_file_exists(self):
        for entry, resolved in _load_declared_agents():
            with self.subTest(agent=entry):
                self.assertTrue(resolved.exists(), f"Declared agent file missing: {entry}")

    def test_each_agent_has_name_and_description(self):
        for entry, resolved in _load_declared_agents():
            with self.subTest(agent=entry):
                text = resolved.read_text(encoding="utf-8")
                fm = _parse_frontmatter(text)
                self.assertIn("name", fm, f"Agent {entry} missing 'name' in frontmatter")
                self.assertIn("description", fm, f"Agent {entry} missing 'description' in frontmatter")

    def test_each_agent_playbook_has_exact_envelope_shape(self):
        for entry, resolved in _load_declared_agents():
            with self.subTest(agent=entry):
                text = resolved.read_text(encoding="utf-8")
                headings = _extract_h2_headings(text)
                self.assertEqual(
                    headings,
                    CANONICAL_ENVELOPE_SECTIONS,
                    f"Agent {entry} envelope must be exactly {CANONICAL_ENVELOPE_SECTIONS} in order, got {headings}",
                )

    def test_each_agent_playbook_forbids_writes(self):
        for entry, resolved in _load_declared_agents():
            with self.subTest(agent=entry):
                text = resolved.read_text(encoding="utf-8")
                body_lower = text.lower()
                self.assertTrue(
                    "never" in body_lower and "set_param" in body_lower
                    or "do not" in body_lower and "write" in body_lower
                    or "read-only" in body_lower,
                    f"Agent {entry} must contain write-prohibition declaration",
                )

    def test_each_agent_playbook_requires_explicit_context(self):
        for entry, resolved in _load_declared_agents():
            with self.subTest(agent=entry):
                text = resolved.read_text(encoding="utf-8")
                body_lower = text.lower()
                has_session_req = "session" in body_lower and ("dispatch" in body_lower or "provided" in body_lower or "required" in body_lower)
                has_model_req = "model" in body_lower and ("dispatch" in body_lower or "provided" in body_lower or "required" in body_lower)
                self.assertTrue(
                    has_session_req and has_model_req,
                    f"Agent {entry} must declare explicit session/model context requirement",
                )


if __name__ == "__main__":
    unittest.main()
