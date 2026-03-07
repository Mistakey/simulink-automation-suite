# PR2 Schema and Context Controls Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add machine-readable CLI introspection and explicit output controls so agents can discover capabilities and constrain response size deterministically.

**Architecture:** Extend `sl_core.py` with a schema action and JSON contract entries, then add scan/inspect output controls in parser + runtime path. Apply deterministic sorting before clipping so repeated runs with same model state are stable.

**Tech Stack:** Python 3, `argparse`, `unittest`, existing fake-engine test style

---

Skill references: `@test-driven-development`, `@verification-before-completion`

### Task 1: Add `schema` Introspection Action

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Create: `tests/test_schema_action.py`

**Step 1: Write the failing test**

Add tests for:
- `schema` action parseability
- JSON mode support: `{"action":"schema"}`
- response contains actions/fields/type metadata

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_schema_action.py" -v`
Expected: FAIL (action not implemented).

**Step 3: Write minimal implementation**

Implement schema response builder in `sl_core.py`:
- include action names
- include field metadata (`type`, `required`, `default`)
- include canonical error code list and examples

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_schema_action.py" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_core.py tests/test_schema_action.py
git commit -m "feat(core): add schema introspection action for agents"
```

### Task 2: Add Scan Output Controls

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Modify: `skills/simulink_scan/scripts/sl_scan.py`
- Create: `tests/test_scan_output_controls.py`

**Step 1: Write the failing test**

Add tests for:
- `scan --max-blocks N` truncates and reports `total_count`/`truncated`
- invalid max (`<=0`) returns `invalid_input`
- `scan --fields "name"` projects block objects to requested fields

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_scan_output_controls.py" -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement:
- parser flags for scan controls
- JSON fields for scan controls
- deterministic sort by block path before clipping
- projection and clipping metadata

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_scan_output_controls.py" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_core.py skills/simulink_scan/scripts/sl_scan.py tests/test_scan_output_controls.py
git commit -m "feat(scan): add output limits and field projection"
```

### Task 3: Add Inspect Output Controls

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Modify: `skills/simulink_scan/scripts/sl_scan.py`
- Create: `tests/test_inspect_output_controls.py`

**Step 1: Write the failing test**

Add tests for:
- `inspect --param All --max-params N` clips parameter outputs deterministically
- invalid max (`<=0`) returns `invalid_input`
- optional `--fields` projection for inspect response sections

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_inspect_output_controls.py" -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement inspect controls:
- sort parameter keys before clipping
- apply limit to `available_params` + `values` + `parameter_meta`
- add truncation metadata

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_inspect_output_controls.py" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_core.py skills/simulink_scan/scripts/sl_scan.py tests/test_inspect_output_controls.py
git commit -m "feat(inspect): add deterministic parameter clipping controls"
```

### Task 4: Deterministic Ordering for Models/Blocks/Params

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_scan.py`
- Modify: `tests/test_scan_behavior.py`
- Modify: `tests/test_inspect_active.py`

**Step 1: Write the failing test**

Add tests proving stable ordered outputs for:
- `list_opened`
- `scan blocks`
- inspect parameter list outputs

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_scan_behavior.py" -v`
Run: `python -m unittest discover -s tests -p "test_inspect_active.py" -v`
Expected: FAIL on unsorted behavior.

**Step 3: Write minimal implementation**

Sort outputs consistently before serialization.

**Step 4: Run test to verify it passes**

Run both commands again.
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_scan.py tests/test_scan_behavior.py tests/test_inspect_active.py
git commit -m "refactor(output): enforce deterministic ordering for agent repeatability"
```

### Task 5: Docs + Full Verification

**Files:**
- Modify: `README.md`
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `skills/simulink_scan/reference.md`

**Step 1: Document schema and output controls**

Add examples for:
- `schema`
- `max-blocks`, `max-params`
- field projection and truncation metadata

**Step 2: Run full regression**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: all tests pass.

**Step 3: Commit**

```bash
git add README.md skills/simulink_scan/SKILL.md skills/simulink_scan/reference.md
git commit -m "docs: add schema and output-control guidance"
```
