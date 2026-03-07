# Plugin Suite Positioning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reposition the plugin manifest and top-level docs from scan-only wording to a future-proof Simulink automation suite while keeping current Python runtime structure unchanged.

**Architecture:** Keep a single plugin product boundary (`simulink-automation-suite`) and keep current skill/runtime implementation intact (`simulink-scan` + existing Python scripts). Add manifest/docs contracts that make room for future additional skills (for example edit) without introducing script splitting in this change.

**Tech Stack:** Claude Code plugin manifest (`.claude-plugin/plugin.json`), Markdown docs, Python `unittest`.

---

### Task 1: Add manifest contract test first

**Files:**
- Create: `tests/test_plugin_manifest_contract.py`
- Test: `tests/test_plugin_manifest_contract.py`

**Step 1: Write the failing test**

- Add assertions for:
  - plugin name equals `simulink-automation-suite`
  - description includes `suite`
  - manifest declares `skills` array containing `./skills/`
  - no explicit `hooks` key

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_plugin_manifest_contract.py -v`  
Expected: FAIL on current name/skills.

**Step 3: Commit**

This plan keeps commit steps as optional checkpoints in the current session.

### Task 2: Update manifest and user-facing plugin docs

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `README.md`
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `skills/simulink_scan/reference.md`

**Step 1: Update plugin manifest metadata**

- Rename plugin to `simulink-automation-suite`.
- Keep current author metadata.
- Add `skills` array for explicit plugin capability discovery.
- Add suite-oriented keywords.
- Keep runtime behavior unchanged.

**Step 2: Update top-level README positioning**

- Distinguish plugin name vs current skill name.
- Keep scan examples valid while making suite roadmap explicit.
- State current constraint: no core script splitting in this change.
- State future direction: migrate to shared MCP core.

**Step 3: Update scan skill docs with suite context**

- Keep scan skill read-only contract unchanged.
- Add brief statement that it is one skill within the broader suite.

### Task 3: Add manifest schema notes and verify

**Files:**
- Create: `.claude-plugin/PLUGIN_SCHEMA_NOTES.md`
- Test: `tests/test_plugin_manifest_contract.py`
- Test: `python -m unittest discover -s tests -p "test_*.py" -v`

**Step 1: Add local schema notes**

- Document validator constraints used in this repo:
  - `version` required
  - path fields as arrays
  - no explicit default `hooks/hooks.json`
  - explicit positioning for future multi-skill suite

**Step 2: Re-run targeted test**

Run: `python -m unittest tests/test_plugin_manifest_contract.py -v`  
Expected: PASS.

**Step 3: Re-run full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`  
Expected: PASS with zero failures.
