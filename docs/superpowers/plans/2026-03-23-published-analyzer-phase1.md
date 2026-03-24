# Published Analyzer Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a `simulink-analyzer` read-analysis agent alongside the existing `simulink-automation` skill, with explicit handoff contract, six-section output envelope, and full test/doc/manifest coverage.

**Architecture:** A single agent markdown file (`agents/simulink-analyzer.md`) with YAML frontmatter and inline playbook handles all read-analysis delegation. The existing skill gains a Responsibility & Handoff section that serves as a product contract for routing decisions. Version bumps to 2.2.0 across plugin.json, marketplace.json, and core.py schema.

**Tech Stack:** Python unittest, YAML frontmatter, Markdown, JSON manifests

**Spec:** `docs/superpowers/specs/2026-03-22-published-analyzer-phase1-design.md`

---

## File Structure

### Files to Create

| File | Responsibility |
|------|---------------|
| `agents/simulink-analyzer.md` | Agent definition: YAML frontmatter (name, description, model, tools) + inline playbook (role, CLI pattern, strategies, output envelope, constraints) |
| `tests/test_agent_definition_contract.py` | Contract tests for agent files declared in plugin.json `agents` array |

### Files to Modify

| File | Change |
|------|--------|
| `.claude-plugin/plugin.json` | Add `agents` array, bump version to `2.2.0`, update description |
| `.claude-plugin/marketplace.json` | Bump version to `2.2.0`, update description to match plugin.json |
| `simulink_cli/core.py:57` | Bump schema version from `"2.1"` to `"2.2"` |
| `skills/simulink_automation/SKILL.md` | Add Responsibility & Handoff section, trim read-analysis workflow guidance |
| `tests/test_plugin_manifest_contract.py` | Add 4 tests: agents key exists, non-empty list, .md paths, files exist on disk |
| `tests/test_docs_contract.py` | Add 8 tests: handoff section structure (6 tests) + README agent mentions (2 tests) |
| `README.md` | Update to dual-capability narrative (analyzer agent + automation skill) |
| `README.zh-CN.md` | Update to dual-capability narrative (Chinese) |

---

## Task 1: Extend plugin manifest contract tests for agents

**Files:**
- Modify: `tests/test_plugin_manifest_contract.py`

- [ ] **Step 1: Write four failing tests for agents manifest contract**

```python
def test_manifest_declares_agents_field(self):
    manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
    self.assertIn("agents", manifest)

def test_manifest_agents_is_nonempty_list(self):
    manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
    agents = manifest.get("agents", [])
    self.assertIsInstance(agents, list)
    self.assertGreater(len(agents), 0)

def test_manifest_agent_entries_are_md_paths(self):
    manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in manifest.get("agents", []):
        self.assertIsInstance(entry, str)
        self.assertTrue(entry.endswith(".md"), f"Agent entry must be .md path: {entry}")

def test_manifest_declared_agent_files_exist(self):
    manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in manifest.get("agents", []):
        agent_path = REPO_ROOT / entry.lstrip("./")
        self.assertTrue(agent_path.exists(), f"Declared agent file missing: {entry}")
```

Append these four methods to the `PluginManifestContractTests` class in `tests/test_plugin_manifest_contract.py`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_plugin_manifest_contract -v`
Expected: 4 FAIL (plugin.json has no `agents` key yet)

- [ ] **Step 3: Commit test additions**

```bash
git add tests/test_plugin_manifest_contract.py
git commit -m "test: add plugin manifest contract tests for agents field"
```

---

## Task 2: Update plugin.json to declare agents

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Add agents array and update description in plugin.json**

Replace the full plugin.json content with:

```json
{
  "name": "simulink-automation-suite",
  "description": "Simulink automation suite plugin for Claude Code with model analysis agent and parameter editing skill.",
  "version": "2.1.0",
  "author": {
    "name": "kelch"
  },
  "skills": [
    "./skills/"
  ],
  "agents": [
    "./agents/simulink-analyzer.md"
  ],
  "keywords": [
    "simulink",
    "matlab",
    "automation",
    "claude-code",
    "agent-first",
    "scan",
    "analysis",
    "edit"
  ]
}
```

Note: version stays at `2.1.0` for now — version bump is Task 8.

- [ ] **Step 2: Run manifest contract tests**

Run: `python -m unittest tests.test_plugin_manifest_contract -v`
Expected: `test_manifest_declares_agents_field` PASS, `test_manifest_agents_is_nonempty_list` PASS, `test_manifest_agent_entries_are_md_paths` PASS, `test_manifest_declared_agent_files_exist` FAIL (agent file doesn't exist yet — expected)

- [ ] **Step 3: Commit manifest change**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: declare agents array in plugin.json with explicit file path"
```

---

## Task 3: Write agent definition contract tests

**Files:**
- Create: `tests/test_agent_definition_contract.py`

- [ ] **Step 1: Write the full test file**

```python
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
                    or "禁止" in body_lower and "写" in body_lower
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_agent_definition_contract -v`
Expected: FAIL — agent file does not exist yet

- [ ] **Step 3: Commit test file**

```bash
git add tests/test_agent_definition_contract.py
git commit -m "test: add agent definition contract tests for envelope, writes, context"
```

---

## Task 4: Create the analyzer agent file

**Files:**
- Create: `agents/simulink-analyzer.md`

- [ ] **Step 1: Create the agents directory and agent file**

```bash
mkdir -p agents
```

Write `agents/simulink-analyzer.md`:

```markdown
---
name: simulink-analyzer
description: Dispatched for Simulink model analysis — topology scanning, block search, connection tracing, parameter inspection, and multi-step read workflows. Returns structured findings without polluting conversation context.
model: sonnet
color: blue
tools:
  - Bash
  - Read
  - Grep
  - Glob
---

You are a read-only Simulink model analyzer. You execute CLI analysis commands and return structured findings.

**You are read-only.** Never execute `set_param`, `model_new`, `model_open`, or `model_save`. Do not write to or mutate any model.

**Context comes from dispatch.** Session and model are provided by the dispatcher. Do not call `session`, `list_opened`, or any discovery action to infer them.

### CLI Invocation

```
python -m simulink_cli --json '{"action":"<action>", "session":"<session>", "model":"<model>", ...}'
```

Call `schema` once at the start to get the full action catalog if you need field details:

```
python -m simulink_cli --json '{"action":"schema"}'
```

### Analysis Strategies

- **Topology overview**: `scan` (shallow first, recursive only if needed). Use `max_blocks` and `fields` to keep output compact.
- **Targeted search**: `find` by name pattern and/or block type. Use `max_results` to bound output.
- **Signal tracing**: `connections` with `direction`, `depth`, `detail`. Use `max_edges` to bound output.
- **Parameter audit**: `inspect` with `param=All` for full parameter list, or specific param for targeted lookup. Use `max_params` and `fields` to bound output.
- **Multi-step**: chain actions as needed — e.g., scan → find → inspect → connections for a complete subsystem audit.

Always start with the narrowest scope that answers the question. Escalate breadth only when needed.

### Output Format

Every response must use exactly this six-section envelope. No additional sections. No reordering.

## Context
- Session: {session_name}
- Model: {model_name}
- Scope: {subsystem or "full model"}

## Answer
[Direct answer to the task, 1–5 sentences. Include quantitative data where applicable.]

## Evidence
- [Key data points supporting the answer, one per line]

## Actions Performed
- action(key_params) → key result metrics (e.g., total_count=47, truncated=false)

## Limitations
- [Truncations, unverified items, or speculative conclusions. "None" if analysis is complete.]

## Suggested Followup
- [Recommended next step if analysis is incomplete. "None" if complete.]
```

- [ ] **Step 2: Run agent definition contract tests**

Run: `python -m unittest tests.test_agent_definition_contract -v`
Expected: 6 PASS

- [ ] **Step 3: Run manifest agent file existence test**

Run: `python -m unittest tests.test_plugin_manifest_contract.PluginManifestContractTests.test_manifest_declared_agent_files_exist -v`
Expected: PASS

- [ ] **Step 4: Commit agent file**

```bash
git add agents/simulink-analyzer.md
git commit -m "feat: add simulink-analyzer agent with playbook and output envelope"
```

---

## Task 5: Add handoff contract tests to test_docs_contract.py

**Files:**
- Modify: `tests/test_docs_contract.py`

- [ ] **Step 1: Write 8 new tests — 6 for handoff contract, 2 for README agent mentions**

Add these imports at the top of the file if not already present:

```python
import json
import re
```

Add these constants after the existing path constants:

```python
PLUGIN_MANIFEST_PATH = REPO_ROOT / ".claude-plugin" / "plugin.json"
```

Add these helper and methods to the `DocsContractTests` class:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_docs_contract -v`
Expected: 8 new tests FAIL (no handoff section yet, no analyzer mention in README yet)

- [ ] **Step 3: Commit test additions**

```bash
git add tests/test_docs_contract.py
git commit -m "test: add handoff contract and README agent coverage tests"
```

---

## Task 6: Update SKILL.md with Responsibility & Handoff section

**Files:**
- Modify: `skills/simulink_automation/SKILL.md`

- [ ] **Step 1: Add Responsibility & Handoff section after Workflow Strategy**

Insert the following section between `## Workflow Strategy` and `## Write Safety Model`:

```markdown
## Responsibility & Handoff

This skill and the `simulink-analyzer` agent have non-overlapping responsibilities.

### Direct Handling (this skill)

The following actions are handled directly without dispatching the agent:

| Action | Reason |
|--------|--------|
| `session` (list/current/use/clear) | Meta-query; main agent needs session context for dispatch decisions |
| `list_opened` | Meta-query; main agent needs model list for dispatch decisions |
| `schema` | Self-discovery; main agent may need the action catalog |
| `highlight` | UI side-effect; no analysis output to isolate |
| `inspect` (specific target + specific param) | Single-value response; main agent needs the value in context |
| `set_param` | Write operation; requires user interaction for safety |
| `model_new` / `model_open` / `model_save` | Write/lifecycle operations |

### Delegate to simulink-analyzer agent

The following actions are delegated to the analyzer agent for context isolation:

| Action | Reason |
|--------|--------|
| `scan` (any configuration) | Topology output; potentially large |
| `find` (any criteria) | Search results; potentially large |
| `connections` (any configuration) | Connection graph; potentially large |
| `inspect` (no specific param or param=All) | Full parameter list; potentially large |
| Multi-step read analysis workflows | Workflow-level context isolation |

Before dispatching, resolve session and model via direct `session current` or `list_opened`, then provide them explicitly to the agent.

### Composite Requests

When a user request involves both analysis and modification (e.g., "check the PID parameters, then set Kp to 2.0"):

1. Dispatch the `simulink-analyzer` agent for the analysis portion first.
2. Use the analysis results to execute the write workflow directly via this skill.

Always analyze before writing. Never combine analysis delegation and write execution in a single step.
```

- [ ] **Step 2: Trim the Workflow Strategy section**

Replace the existing Workflow Strategy content to remove multi-step read analysis guidance now owned by the agent. The section should focus on direct-handling cases:

Replace:
```markdown
## Workflow Strategy

1. **Discover** — `list_opened` to see available models; `session list` if multiple MATLAB sessions exist.
2. **Understand** — `scan` (shallow first, recursive only when needed), `find` to locate blocks, `inspect` to read parameters.
3. **Navigate** — `connections` for upstream/downstream analysis, `highlight` for visual location.
4. **Modify** — `set_param` with dry-run preview before any write. See Write Safety Model below.
5. **Verify** — `inspect` the target after write to confirm the change took effect.

Default to shallow scans. Escalate to recursive/hierarchy only when explicitly requested.
Always read and understand the model before modifying. One parameter per `set_param` invocation.
```

With:
```markdown
## Workflow Strategy

1. **Discover** — `list_opened` to see available models; `session list` if multiple MATLAB sessions exist.
2. **Quick lookup** — `inspect` with a specific target and specific param for single-value checks; `highlight` for visual location.
3. **Deep analysis** — delegate to `simulink-analyzer` agent (see Responsibility & Handoff).
4. **Modify** — `set_param` with dry-run preview before any write. See Write Safety Model below.
5. **Verify** — `inspect` the target after write to confirm the change took effect.

One parameter per `set_param` invocation. Always read and understand the model before modifying.
```

- [ ] **Step 3: Run handoff contract tests**

Run: `python -m unittest tests.test_docs_contract -v`
Expected: all 6 handoff tests PASS, 2 README tests still FAIL

- [ ] **Step 4: Commit SKILL.md changes**

```bash
git add skills/simulink_automation/SKILL.md
git commit -m "feat: add Responsibility & Handoff contract to SKILL.md"
```

---

## Task 7: Update README files with dual-capability narrative

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Update README.md**

In `README.md`, replace the intro block (lines 9–13) with:

```markdown
Simulink Automation Suite is a Claude Code plugin for Simulink automation workflows through MATLAB Engine for Python.

- Canonical plugin name: `simulink-automation-suite`
- **Read Analysis** — the `simulink-analyzer` agent autonomously explores model topology, traces connections, audits parameters, and returns structured findings without polluting conversation context.
- **Write Automation** — the `simulink-automation` skill guides safe parameter modification with dry-run preview, precondition guards, and rollback support.
- Runtime Python module path: `simulink_cli` (unified CLI entrypoint)
```

In `README.md`, replace the "How It Works" step 1 (line 46) with:

```markdown
1. Claude Code invokes the `simulink-automation` skill for write/meta tasks, or dispatches the `simulink-analyzer` agent for read analysis.
```

In `README.md`, update the "What's Inside" tree (around line 290–294) to include the agents directory:

```text
agents/                 # Published agent definitions
└── simulink-analyzer.md  # Read-analysis agent (topology, search, connections, inspection)
skills/                 # Plugin skill definitions (docs only, no Python code)
└── simulink_automation/  # Write automation + meta-query skill
    ├── SKILL.md
    └── reference.md
```

In `README.md`, update the Roadmap section (lines 310–312):

```markdown
- **Current (v2.2.x):** read-only analysis via `simulink-analyzer` agent, guarded parameter modification and model lifecycle management via `simulink-automation` skill, all through the unified `simulink_cli` package.
- **Next:** strengthen agent workflow orchestration and reliability while preserving deterministic contracts and recovery paths.
- **Future:** add new skills for build/repair scenarios without renaming the plugin (`simulink-automation-suite` remains the stable identity).
```

- [ ] **Step 2: Update README.zh-CN.md**

In `README.zh-CN.md`, replace the intro block (lines 9–13) with:

```markdown
Simulink Automation Suite 是一个基于 MATLAB Engine for Python 的 Claude Code 插件，用于 Simulink 自动化工作流。

- 插件标准名称：`simulink-automation-suite`
- **只读分析** — `simulink-analyzer` agent 自主探索模型拓扑、追踪连接、审计参数，并返回结构化分析结果，不会污染对话上下文。
- **写入自动化** — `simulink-automation` 技能引导安全的参数修改，提供 dry-run 预览、前置条件守卫和回滚支持。
- 运行时 Python 模块路径：`simulink_cli`（统一 CLI 入口）
```

In `README.zh-CN.md`, replace the "工作方式" step 1 (line 46) with:

```markdown
1. Claude Code 调用 `simulink-automation` 技能处理写入/元查询任务，或 dispatch `simulink-analyzer` agent 进行只读分析。
```

In `README.zh-CN.md`, update the "仓库内容" tree (around line 289–294) to include agents:

```text
agents/                 # 已发布的 Agent 定义
└── simulink-analyzer.md  # 只读分析 Agent（拓扑、搜索、连接、参数审计）
skills/                 # 插件技能定义（仅文档，无 Python 代码）
└── simulink_automation/  # 写入自动化 + 元查询技能
    ├── SKILL.md
    └── reference.md
```

In `README.zh-CN.md`, update the 路线图 section (lines 310–312):

```markdown
- **当前阶段（v2.2.x）：** 通过 `simulink-analyzer` agent 进行只读分析，通过 `simulink-automation` 技能进行 guarded 参数修改和模型生命周期管理，均通过统一的 `simulink_cli` 包。
- **下一阶段：** 在保持可预测契约与恢复链路的前提下，增强 Agent 工作流编排与可靠性。
- **后续阶段：** 通过新增技能扩展到 build/repair 场景，且保持插件标识 `simulink-automation-suite` 不变。
```

- [ ] **Step 3: Run README docs contract tests**

Run: `python -m unittest tests.test_docs_contract -v`
Expected: ALL PASS (including the 2 README agent tests)

- [ ] **Step 4: Commit README changes**

```bash
git add README.md README.zh-CN.md
git commit -m "docs: update READMEs with dual-capability narrative (analyzer agent + automation skill)"
```

---

## Task 8: Version bump to 2.2.0

**Files:**
- Modify: `.claude-plugin/plugin.json` (version field only)
- Modify: `.claude-plugin/marketplace.json` (version + description)
- Modify: `simulink_cli/core.py:57`

- [ ] **Step 1: Bump plugin.json version from 2.1.0 to 2.2.0**

In `.claude-plugin/plugin.json`, change:
```json
"version": "2.1.0",
```
to:
```json
"version": "2.2.0",
```

- [ ] **Step 2: Bump marketplace.json version and update description**

In `.claude-plugin/marketplace.json`, change `plugins[0].version` from `"2.1.0"` to `"2.2.0"`. Change `plugins[0].description` to match plugin.json:
```json
"description": "Simulink automation suite plugin for Claude Code with model analysis agent and parameter editing skill.",
```

Verify the top-level `metadata.description` remains unchanged (it describes the marketplace, not the plugin):
```json
"description": "Simulink automation suite marketplace for Claude Code plugins."
```

- [ ] **Step 3: Bump schema version in core.py**

In `simulink_cli/core.py:57`, change:
```python
"version": "2.1",
```
to:
```python
"version": "2.2",
```

- [ ] **Step 4: Run marketplace manifest contract tests**

Run: `python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v`
Expected: ALL PASS

- [ ] **Step 5: Commit version bumps**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json simulink_cli/core.py
git commit -m "chore: bump version to 2.2.0 (plugin, marketplace, schema)"
```

---

## Task 9: Full verification

- [ ] **Step 1: Run full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: ALL PASS, no regressions

- [ ] **Step 2: Run agent and manifest contract tests specifically**

Run: `python -m unittest tests.test_agent_definition_contract -v`
Expected: 6 PASS

Run: `python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v`
Expected: ALL PASS

- [ ] **Step 3: Run docs contract tests specifically**

Run: `python -m unittest tests.test_docs_contract -v`
Expected: ALL PASS

- [ ] **Step 4: Run release metadata check**

Run: `python scripts/check_release_metadata.py --tag v2.2.0`
Expected: PASS

- [ ] **Step 5: Verify schema output**

Run: `python -m simulink_cli schema`
Expected: version shows "2.2", same action set as before (no new actions, no removed actions)

- [ ] **Step 6: Run plugin validation**

Run: `claude plugin validate .`
Expected: PASS

- [ ] **Step 7: Final commit if any fixups needed**

If any test failures required fixups, commit them:
```bash
git add -A
git commit -m "fix: address verification issues from full test suite run"
```
