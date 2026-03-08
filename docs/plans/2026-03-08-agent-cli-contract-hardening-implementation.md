# Agent CLI Contract Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade `simulink-scan` to a schema-first, budget-controlled, agent-friendly CLI contract across all actions.

**Architecture:** Introduce canonical action metadata in `sl_core.py` and derive schema output/validation behavior from it. Keep runtime behavior read-only while expanding output control parity (`max_*`, `fields`) across high-volume actions. Enforce doc/runtime/test alignment with expanded contract tests.

**Tech Stack:** Python 3.10+, `argparse`, `unittest`, existing modules under `skills/simulink_scan/scripts/*`.

---

### Task 1: Add Failing Tests for Structured Schema Contract

**Files:**
- Modify: `tests/test_schema_action.py`
- Test: `tests/test_schema_action.py`

**Step 1: Write the failing tests**

Add tests to enforce:

- `schema` payload includes top-level `version`.
- each action includes `description` and `fields`.
- each field is metadata object containing `type` and `required`.
- `connections.direction` has enum `["upstream","downstream","both"]`.
- `connections.depth` has default `1`.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_schema_action -v`  
Expected: FAIL because schema currently returns raw class strings.

**Step 3: Add minimal schema metadata scaffolding in `sl_core.py`**

Introduce canonical action-field metadata constants without fully wiring parser/validation yet.

**Step 4: Run test to verify failure reason shifts**

Run: `python -m unittest tests.test_schema_action -v`  
Expected: Remaining failures now point to incomplete schema serialization.

**Step 5: Commit**

```bash
git add tests/test_schema_action.py skills/simulink_scan/scripts/sl_core.py
git commit -m "test(schema): require structured action metadata contract"
```

### Task 2: Implement Structured Schema Serialization in `sl_core.py`

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Test: `tests/test_schema_action.py`

**Step 1: Write a focused failing test for field metadata serialization**

Add assertion that `schema.actions.connections.fields.direction.type == "string"` and `required/default/enum` are present.

**Step 2: Run the focused test to fail**

Run:  
`python -m unittest tests.test_schema_action.SchemaActionTests.test_schema_connections_field_metadata_shape -v`

**Step 3: Implement minimal serialization**

- Build `ACTION_DEFINITIONS` with field metadata.
- Replace `_JSON_FIELD_TYPES`-driven schema emission with `ACTION_DEFINITIONS`.
- Keep existing error code list.

**Step 4: Run all schema tests**

Run: `python -m unittest tests.test_schema_action -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_core.py tests/test_schema_action.py
git commit -m "feat(schema): emit structured action contract metadata"
```

### Task 3: Add Failing Tests for Unified JSON Constraints

**Files:**
- Modify: `tests/test_json_input_mode.py`
- Modify: `tests/test_input_validation.py`
- Test: `tests/test_json_input_mode.py`
- Test: `tests/test_input_validation.py`

**Step 1: Write failing tests**

Add JSON-mode tests:

- reject `connections.depth=0` as `invalid_input`.
- reject unknown `connections.detail` enum value.
- reject wrong type for `connections.include_handles`.

Add validation tests:

- reject non-positive values for `scan.max_blocks`, `inspect.max_params`, `connections.max_edges`.
- reject unsupported fields in all actions.

**Step 2: Run tests to verify failures**

Run:  
`python -m unittest tests.test_json_input_mode tests.test_input_validation -v`

**Step 3: Implement minimal validation mapping in `sl_core.py`**

- unify constraints in action metadata (enum/minimum).
- enforce metadata-based checks during JSON parsing and `validate_args`.

**Step 4: Re-run tests**

Run:  
`python -m unittest tests.test_json_input_mode tests.test_input_validation -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_json_input_mode.py tests/test_input_validation.py skills/simulink_scan/scripts/sl_core.py
git commit -m "feat(validation): unify json and flag constraints across actions"
```

### Task 4: Add Failing Tests for Connections Output Controls

**Files:**
- Modify: `tests/test_connections_behavior.py`
- Create: `tests/test_connections_output_controls.py`
- Test: `tests/test_connections_behavior.py`
- Test: `tests/test_connections_output_controls.py`

**Step 1: Write failing tests**

Cover:

- `max_edges` truncates edges and sets `truncated=true`.
- response includes `total_edges`.
- `fields` projects top-level keys.
- stable ordering of `edges`.

**Step 2: Run tests to verify failure**

Run:  
`python -m unittest tests.test_connections_behavior tests.test_connections_output_controls -v`

**Step 3: Implement minimal runtime support in `sl_scan.py`**

- add `max_edges` and `fields` args to `get_block_connections`.
- apply clipping + metadata.
- apply top-level projection helper.

**Step 4: Re-run tests**

Run:  
`python -m unittest tests.test_connections_behavior tests.test_connections_output_controls -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_connections_behavior.py tests/test_connections_output_controls.py skills/simulink_scan/scripts/sl_scan.py
git commit -m "feat(connections): add max_edges and fields output controls"
```

### Task 5: Wire Parser/Runtime for New Controls and Metadata Defaults

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Modify: `skills/simulink_scan/scripts/sl_scan.py`
- Test: `tests/test_json_input_mode.py`
- Test: `tests/test_connections_output_controls.py`

**Step 1: Add failing parser tests**

Assert parser accepts:

- `connections --max-edges N`
- `connections --fields "target,edges"`

**Step 2: Run focused parser tests**

Run:  
`python -m unittest tests.test_json_input_mode -v`

**Step 3: Implement parser/runtime wiring**

- add CLI flags for `connections` output controls.
- pass normalized values to `get_block_connections`.

**Step 4: Re-run focused tests**

Run:  
`python -m unittest tests.test_json_input_mode tests.test_connections_output_controls -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_core.py skills/simulink_scan/scripts/sl_scan.py tests/test_json_input_mode.py tests/test_connections_output_controls.py
git commit -m "feat(cli): wire connections output controls into parser and runtime"
```

### Task 6: Add Failing Docs Contract Tests for Hardened Schema and Controls

**Files:**
- Modify: `tests/test_docs_contract.py`
- Test: `tests/test_docs_contract.py`

**Step 1: Write failing docs tests**

Require docs to mention:

- structured `schema` purpose and `connections` defaults.
- `connections` JSON example.
- `connections` output controls (`max_edges`, `fields`).

**Step 2: Run docs tests to fail**

Run: `python -m unittest tests.test_docs_contract -v`

**Step 3: Keep runtime unchanged**

This task is docs-contract-first.

**Step 4: Re-run docs tests**

Run: `python -m unittest tests.test_docs_contract -v`  
Expected: still FAIL until docs update task.

**Step 5: Commit**

```bash
git add tests/test_docs_contract.py
git commit -m "test(docs): require hardened schema and controls in docs"
```

### Task 7: Update All Docs for Hardened Contract

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `skills/simulink_scan/reference.md`
- Modify: `skills/simulink_scan/test-scenarios.md`
- Test: `tests/test_docs_contract.py`

**Step 1: Update docs**

Include:

- `connections` flags + JSON examples.
- `connections` defaults and control flags.
- note that `schema` now contains structured field metadata.

**Step 2: Run docs tests**

Run: `python -m unittest tests.test_docs_contract -v`  
Expected: PASS.

**Step 3: Run targeted integration tests**

Run:  
`python -m unittest tests.test_schema_action tests.test_json_input_mode tests.test_input_validation tests.test_connections_output_controls tests.test_docs_contract -v`  
Expected: PASS.

**Step 4: Commit**

```bash
git add README.md README.zh-CN.md skills/simulink_scan/SKILL.md skills/simulink_scan/reference.md skills/simulink_scan/test-scenarios.md tests/test_docs_contract.py
git commit -m "docs(contract): align docs with hardened schema and output controls"
```

### Task 8: Full Verification and Final Integration Check

**Files:**
- Verify only

**Step 1: Run full suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`  
Expected: all tests pass.

**Step 2: Validate representative CLI calls**

Run:

- `python -m skills.simulink_scan schema`
- `python -m skills.simulink_scan --json "{\"action\":\"connections\",\"target\":\"<block>\",\"detail\":\"summary\"}"`

Expected: structured schema and stable error/output envelopes.

**Step 3: Inspect changed files**

Run: `git diff --name-only <base>..HEAD`  
Expected: only intended runtime/tests/docs files changed.

**Step 4: Commit any final polish if needed**

```bash
git add -A
git commit -m "chore: finalize cli contract hardening"
```

**Step 5: Prepare merge/PR summary**

Summarize:

- structured schema migration.
- unified validation.
- output budget parity.
- docs/test contract hardening evidence.
