# MATLAB Session Error Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add deterministic `engine_unavailable` vs `no_session` behavior so AI gives correct user guidance, and document MATLAB prerequisites in README and skill docs.

**Architecture:** Keep current runtime flow but emit stable error code at the source (`sl_session.py`) and map it in `sl_core.py` into deterministic JSON envelope. Extend tests first (TDD) for runtime mapping, schema contract, session behavior, and docs contract, then implement minimal code/doc updates to satisfy tests.

**Tech Stack:** Python 3, `unittest`, Claude plugin runtime, markdown docs.

---

### Task 1: Add failing contract tests for `engine_unavailable`

**Files:**
- Modify: `tests/test_runtime_error_mapping.py`
- Modify: `tests/test_schema_action.py`

**Step 1: Write failing tests**

Add in `tests/test_runtime_error_mapping.py`:

```python
    def test_known_session_error_codes_map_stably(self):
        for code in (
            "session_required",
            "session_not_found",
            "no_session",
            "engine_unavailable",
        ):
            result = map_runtime_error(RuntimeError(code))
            self.assertEqual(result["error"], code)
            self.assertIn("message", result)
            self.assertIn("details", result)
            self.assertIn("suggested_fix", result)
```

Add in `tests/test_schema_action.py`:

```python
    def test_schema_action_includes_engine_unavailable_error_code(self):
        args = parse_request_args(self.parser, ["schema"])
        result = run_action(args)
        self.assertIn("engine_unavailable", result["error_codes"])
```

**Step 2: Run tests to verify failure**

Run:

```bash
python -m unittest tests.test_runtime_error_mapping tests.test_schema_action -v
```

Expected: FAIL because `engine_unavailable` is not yet in mapper/contract.

**Step 3: Commit test-only changes**

```bash
git add tests/test_runtime_error_mapping.py tests/test_schema_action.py
git commit -m "test(contract): require engine_unavailable in mapper and schema"
```

---

### Task 2: Implement core error-code contract and mapping

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Test: `tests/test_runtime_error_mapping.py`
- Test: `tests/test_schema_action.py`

**Step 1: Write minimal implementation**

In `skills/simulink_scan/scripts/sl_core.py`:

1. Add `engine_unavailable` to `_ERROR_CODES`.
2. Add mapper entries in `map_runtime_error()`.

Implementation target:

```python
_ERROR_CODES = [
    "invalid_input",
    "invalid_json",
    "unknown_parameter",
    "json_conflict",
    "engine_unavailable",
    "no_session",
    "session_required",
    "session_not_found",
    ...
]
```

```python
messages = {
    "engine_unavailable": (
        "MATLAB Engine for Python is not available in the current Python environment."
    ),
    "session_required": "Multiple MATLAB sessions found. Pass --session with an exact session name.",
    "session_not_found": "Session not found. Pass an exact session name from `session list` output.",
    "no_session": "No shared MATLAB session found. Ask user to run matlab.engine.shareEngine in MATLAB.",
}

suggested_fixes = {
    "engine_unavailable": (
        "Install/configure MATLAB Engine for Python for the active interpreter, then retry."
    ),
    "session_required": "Run `session list` and pass --session with an exact name.",
    "session_not_found": "Run `session list` and retry with an exact session name.",
    "no_session": "Run matlab.engine.shareEngine in MATLAB, then retry.",
}
```

**Step 2: Run tests to verify pass**

Run:

```bash
python -m unittest tests.test_runtime_error_mapping tests.test_schema_action -v
```

Expected: PASS.

**Step 3: Commit implementation**

```bash
git add skills/simulink_scan/scripts/sl_core.py
git commit -m "feat(error): add engine_unavailable stable contract mapping"
```

---

### Task 3: Add failing session-source tests for engine import failures

**Files:**
- Modify: `tests/test_session_state.py`
- Test: `skills/simulink_scan/scripts/sl_session.py`

**Step 1: Write failing tests**

Add tests in `tests/test_session_state.py`:

```python
    def test_get_matlab_engine_import_failure_returns_engine_unavailable(self):
        with mock.patch("importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(RuntimeError) as context:
                sl_session._get_matlab_engine()
        self.assertEqual(str(context.exception), "engine_unavailable")

    def test_discover_sessions_propagates_engine_unavailable(self):
        with mock.patch.object(
            sl_session, "_get_matlab_engine", side_effect=RuntimeError("engine_unavailable")
        ):
            with self.assertRaises(RuntimeError) as context:
                sl_session.discover_sessions()
        self.assertEqual(str(context.exception), "engine_unavailable")
```

**Step 2: Run tests to verify failure**

Run:

```bash
python -m unittest tests.test_session_state -v
```

Expected: FAIL with current `_get_matlab_engine`/`discover_sessions` behavior.

**Step 3: Commit test-only changes**

```bash
git add tests/test_session_state.py
git commit -m "test(session): require deterministic engine_unavailable source path"
```

---

### Task 4: Implement deterministic `engine_unavailable` behavior in session layer

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_session.py`
- Test: `tests/test_session_state.py`

**Step 1: Write minimal implementation**

In `skills/simulink_scan/scripts/sl_session.py`:

1. Update `_get_matlab_engine()`:

```python
def _get_matlab_engine():
    try:
        import importlib

        return importlib.import_module("matlab.engine")
    except Exception as exc:
        raise RuntimeError("engine_unavailable") from exc
```

2. Update `discover_sessions()` to preserve stable code:

```python
def discover_sessions():
    try:
        engine = _get_matlab_engine()
        return as_list(engine.find_matlab())
    except RuntimeError as exc:
        if str(exc) == "engine_unavailable":
            raise
        raise RuntimeError(f"Failed to discover MATLAB sessions: {exc}")
    except Exception as exc:
        raise RuntimeError(f"Failed to discover MATLAB sessions: {exc}")
```

**Step 2: Run tests to verify pass**

Run:

```bash
python -m unittest tests.test_session_state tests.test_runtime_error_mapping -v
```

Expected: PASS, including existing `no_session` behavior.

**Step 3: Commit implementation**

```bash
git add skills/simulink_scan/scripts/sl_session.py
git commit -m "feat(session): emit engine_unavailable for matlab engine import failures"
```

---

### Task 5: Add failing docs-contract tests for prerequisites and routing

**Files:**
- Modify: `tests/test_docs_contract.py`
- Test: `README.md`
- Test: `README.zh-CN.md`
- Test: `skills/simulink_scan/SKILL.md`
- Test: `skills/simulink_scan/reference.md`

**Step 1: Write failing tests**

Add to `tests/test_docs_contract.py`:

```python
    def test_readme_documents_matlab_prerequisites(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("MATLAB Engine for Python", text)
        self.assertIn("matlab.engine.shareEngine", text)

    def test_skill_and_reference_include_engine_unavailable_route(self):
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        ref_text = REFERENCE_PATH.read_text(encoding="utf-8")
        self.assertIn("engine_unavailable", skill_text)
        self.assertIn("engine_unavailable", ref_text)
```

**Step 2: Run tests to verify failure**

Run:

```bash
python -m unittest tests.test_docs_contract -v
```

Expected: FAIL until docs are updated.

**Step 3: Commit test-only changes**

```bash
git add tests/test_docs_contract.py
git commit -m "test(docs): require matlab prerequisites and engine_unavailable routing docs"
```

---

### Task 6: Update docs (README + skill docs) and verify full suite

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `skills/simulink_scan/reference.md`

**Step 1: Update README docs**

In `README.md` add a `Prerequisites` section that explicitly states:
- MATLAB is installed and accessible.
- MATLAB Engine for Python is installed in the same Python environment.
- MATLAB must run `matlab.engine.shareEngine` before session-bound commands.
- Distinguish troubleshooting for `engine_unavailable` vs `no_session`.

In `README.zh-CN.md` add equivalent Chinese prerequisites and troubleshooting.

**Step 2: Update skill docs**

In `skills/simulink_scan/SKILL.md` recovery routing, add:
- `engine_unavailable` -> install/configure MATLAB Engine for Python in active interpreter.

In `skills/simulink_scan/reference.md`:
- add `engine_unavailable` to common error codes.
- add recovery matrix row with next action and success signal.

**Step 3: Run focused docs tests**

Run:

```bash
python -m unittest tests.test_docs_contract -v
```

Expected: PASS.

**Step 4: Run full regression suite**

Run:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: PASS all tests.

**Step 5: Commit doc changes**

```bash
git add README.md README.zh-CN.md skills/simulink_scan/SKILL.md skills/simulink_scan/reference.md
git commit -m "docs: add matlab engine prerequisites and engine_unavailable recovery guidance"
```

---

### Task 7: Final verification and integration commit

**Files:**
- Verify: full repository

**Step 1: Confirm clean tree and log**

Run:

```bash
git status --short
git log --oneline -n 8
```

Expected: clean working tree; commits reflect TDD progression.

**Step 2: Optional squash strategy decision**

If project policy requires fewer commits, prepare squash plan; otherwise keep granular commits.

**Step 3: Push readiness check**

Run:

```bash
git remote -v
```

Expected: `origin` configured to `https://github.com/Mistakey/simulink-automation-suite.git`.

