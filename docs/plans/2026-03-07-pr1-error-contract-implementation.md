# PR1 Error Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify all CLI and runtime failures under a stable machine-readable error envelope with deterministic error codes.

**Architecture:** Add a centralized error helper module and route all failure paths in `sl_core.py`, `sl_scan.py`, and `sl_session.py` through it. Keep successful payloads backward-compatible where practical, but make all failures code-driven (`error`) and structured (`message`, `details`, `suggested_fix`).

**Tech Stack:** Python 3, `argparse`, `unittest`, existing scripts under `skills/simulink_scan/scripts/`

---

Skill references: `@test-driven-development`, `@verification-before-completion`

### Task 1: Add Central Error Helpers

**Files:**
- Create: `skills/simulink_scan/scripts/sl_errors.py`
- Test: `tests/test_error_contract.py`

**Step 1: Write the failing test**

Add tests asserting helper-generated payload shape and required keys:

```python
def test_make_error_has_stable_shape(self):
    payload = make_error("model_not_found", "Model not opened")
    self.assertEqual(payload["error"], "model_not_found")
    self.assertIn("message", payload)
    self.assertIn("details", payload)
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_error_contract.py" -v`
Expected: FAIL (module/function missing).

**Step 3: Write minimal implementation**

Implement helper functions in `sl_errors.py`:
- `make_error(code, message, details=None, suggested_fix=None)`
- optional utility for preserving/casting details safely.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_error_contract.py" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_errors.py tests/test_error_contract.py
git commit -m "feat(errors): add stable error payload helpers"
```

### Task 2: Migrate `sl_session.py` to Stable Error Envelope

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_session.py`
- Test: `tests/test_session_state.py`

**Step 1: Write the failing test**

Add tests for no-session and state-file failures to assert stable codes and structured fields.

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_session_state.py" -v`
Expected: FAIL on legacy non-standard error payloads.

**Step 3: Write minimal implementation**

Replace string-based errors with helper-driven payloads:
- no session -> `no_session`
- state write failure -> `state_write_failed`
- state clear failure -> `state_clear_failed`

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_session_state.py" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_session.py tests/test_session_state.py
git commit -m "refactor(session): normalize session error payloads"
```

### Task 3: Migrate `sl_scan.py` to Stable Target/Runtime Errors

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_scan.py`
- Modify: `tests/test_scan_behavior.py`
- Modify/Create: `tests/test_inspect_active.py`, `tests/test_error_contract.py`

**Step 1: Write the failing test**

Add/adjust tests for:
- unknown model -> `model_not_found`
- unknown subsystem -> `subsystem_not_found`
- invalid subsystem type -> `invalid_subsystem_type`
- unknown block -> `block_not_found`
- generic runtime fallback -> `runtime_error`

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_scan_behavior.py" -v`
Run: `python -m unittest discover -s tests -p "test_inspect_active.py" -v`
Expected: FAIL with old free-text `error` values.

**Step 3: Write minimal implementation**

Replace free-text `error` returns with stable codes and move verbose context into `message/details`.

**Step 4: Run test to verify it passes**

Run both commands again.
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_scan.py tests/test_scan_behavior.py tests/test_inspect_active.py tests/test_error_contract.py
git commit -m "refactor(scan): convert scan/inspect failures to stable error codes"
```

### Task 4: Normalize CLI Top-Level Exception Mapping

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Modify: `tests/test_runtime_error_mapping.py`
- Modify: `tests/test_json_input_mode.py`

**Step 1: Write the failing test**

Add tests ensuring top-level exception paths emit:
- stable `error` code
- stable `message`
- no `Unexpected error: ...` embedded in `error`

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_runtime_error_mapping.py" -v`
Expected: FAIL on old fallback behavior.

**Step 3: Write minimal implementation**

Update `map_runtime_error`, `map_value_error`, and fallback exception path to emit stable envelope.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_runtime_error_mapping.py" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_core.py tests/test_runtime_error_mapping.py tests/test_json_input_mode.py
git commit -m "refactor(core): enforce stable top-level error contract"
```

### Task 5: Documentation Sync + Full Verification

**Files:**
- Modify: `README.md`
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `skills/simulink_scan/reference.md`

**Step 1: Update docs for new stable error codes**

Document canonical error envelope and revised code list.

**Step 2: Run full regression**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: all tests pass.

**Step 3: Commit**

```bash
git add README.md skills/simulink_scan/SKILL.md skills/simulink_scan/reference.md
git commit -m "docs: document unified error contract"
```
