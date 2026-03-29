# `matlab_eval` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `matlab_eval` action — execute arbitrary MATLAB code and return captured text output.

**Architecture:** New `eval_code()` in transport layer calls MATLAB `evalc`. New action module `matlab_eval.py` follows existing Operational tier pattern (like `simulate_cmd`). Output truncated at 50K chars for context window safety.

**Tech Stack:** Python, MATLAB Engine for Python (`evalc` + async timeout), unittest with mocks.

**Spec:** `docs/superpowers/specs/2026-03-29-matlab-eval-design.md`

---

### Task 1: Transport layer — `eval_code()`

**Files:**
- Modify: `simulink_cli/matlab_transport.py:195-201` (append after `sim`)
- Test: `tests/test_matlab_eval.py` (create)

- [ ] **Step 1: Write failing test for eval_code success path**

Create `tests/test_matlab_eval.py`:

```python
"""Tests for matlab_eval action."""

import unittest
from unittest.mock import MagicMock

from simulink_cli import matlab_transport


class EvalCodeTransportTests(unittest.TestCase):
    def test_eval_code_returns_output_and_warnings(self):
        engine = MagicMock()
        engine.evalc = MagicMock(return_value="ans =\n    3.1416\n")
        engine.lastwarn = MagicMock(side_effect=TypeError)

        result = matlab_transport.eval_code(engine, "pi")

        engine.evalc.assert_called_once_with("pi", nargout=1)
        self.assertEqual(result["value"], "ans =\n    3.1416\n")
        self.assertIsInstance(result["warnings"], list)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_matlab_eval.EvalCodeTransportTests.test_eval_code_returns_output_and_warnings -v`
Expected: FAIL with `AttributeError: module 'simulink_cli.matlab_transport' has no attribute 'eval_code'`

- [ ] **Step 3: Implement eval_code in transport**

Append to `simulink_cli/matlab_transport.py` after the `sim` function (line 201):

```python

def eval_code(engine, code, timeout=30):
    """Execute arbitrary MATLAB code via evalc, returning captured text output.

    Uses async execution for timeout support.  Falls back to synchronous
    evalc when the engine does not support async calls (e.g. test fakes).
    """
    _reset_lastwarn(engine)
    try:
        if hasattr(engine, "evalc_async"):
            future = engine.evalc_async(code, nargout=1)
            value = future.result(timeout=timeout)
        else:
            value = engine.evalc(code, nargout=1)
    except Exception as exc:
        _attach_exception_warnings(exc, _drain_warnings(engine))
        raise
    warnings = _drain_warnings(engine)
    return _result(value=value, warnings=warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_matlab_eval.EvalCodeTransportTests.test_eval_code_returns_output_and_warnings -v`
Expected: PASS

- [ ] **Step 5: Add timeout test**

Append to `EvalCodeTransportTests` in `tests/test_matlab_eval.py`:

```python
    def test_eval_code_timeout_raises(self):
        engine = MagicMock()
        future = MagicMock()
        future.result = MagicMock(side_effect=TimeoutError("timed out"))
        engine.evalc_async = MagicMock(return_value=future)
        engine.lastwarn = MagicMock(side_effect=TypeError)

        with self.assertRaises(TimeoutError):
            matlab_transport.eval_code(engine, "while true; end", timeout=1)

        engine.evalc_async.assert_called_once_with("while true; end", nargout=1)
        future.result.assert_called_once_with(timeout=1)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m unittest tests.test_matlab_eval.EvalCodeTransportTests -v`
Expected: 2 tests PASS

- [ ] **Step 7: Commit**

```bash
git add simulink_cli/matlab_transport.py tests/test_matlab_eval.py
git commit -m "feat: add eval_code to matlab_transport (evalc + async timeout)"
```

---

### Task 2: Action module — `matlab_eval.py` validation

**Files:**
- Create: `simulink_cli/actions/matlab_eval.py`
- Modify: `tests/test_matlab_eval.py` (append validation tests)

- [ ] **Step 1: Write failing validation tests**

Append to `tests/test_matlab_eval.py`:

```python
from simulink_cli.actions import matlab_eval


class MatlabEvalValidationTests(unittest.TestCase):
    def test_valid_args_returns_none(self):
        result = matlab_eval.validate({"code": "pi", "session": None})
        self.assertIsNone(result)

    def test_missing_code_returns_error(self):
        result = matlab_eval.validate({"code": None, "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_empty_code_returns_error(self):
        result = matlab_eval.validate({"code": "", "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_timeout_negative_returns_error(self):
        result = matlab_eval.validate({"code": "pi", "timeout": -1})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_timeout_zero_returns_error(self):
        result = matlab_eval.validate({"code": "pi", "timeout": 0})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_timeout_returns_none(self):
        result = matlab_eval.validate({"code": "pi", "timeout": 10})
        self.assertIsNone(result)

    def test_code_with_newlines_returns_none(self):
        result = matlab_eval.validate({"code": "x = 1;\ndisp(x)", "session": None})
        self.assertIsNone(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_matlab_eval.MatlabEvalValidationTests -v`
Expected: FAIL with `ImportError: cannot import name 'matlab_eval'`

- [ ] **Step 3: Create action module with exports and validate()**

Create `simulink_cli/actions/matlab_eval.py`:

```python
"""matlab_eval action — execute arbitrary MATLAB code and return text output."""

from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_payload_field, validate_text_field

DESCRIPTION = "Execute arbitrary MATLAB code and return captured text output."

FIELDS = {
    "code": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "MATLAB code to execute. Supports multi-line.",
    },
    "timeout": {
        "type": "number",
        "required": False,
        "default": 30,
        "description": "Execution timeout in seconds. Prevents runaway code.",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "MATLAB session name override.",
    },
}

ERRORS = [
    "engine_unavailable",
    "no_session",
    "session_not_found",
    "session_required",
    "eval_failed",
    "eval_timeout",
    "runtime_error",
]

_OUTPUT_MAX_CHARS = 50_000


def validate(args):
    """Validate matlab_eval arguments. Returns error dict or None."""
    code = args.get("code")
    if code is None or (isinstance(code, str) and not code):
        return make_error(
            "invalid_input",
            "Field 'code' is required and must not be empty.",
            details={"field": "code"},
        )
    err = validate_matlab_payload_field("code", code, max_len=100_000)
    if err is not None:
        return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    timeout = args.get("timeout")
    if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
        return make_error(
            "invalid_input",
            "Field 'timeout' must be a positive number.",
            details={"field": "timeout", "value": timeout},
        )

    return None


def execute(args):
    raise NotImplementedError("execute not yet implemented")
```

- [ ] **Step 4: Run validation tests to verify they pass**

Run: `python -m unittest tests.test_matlab_eval.MatlabEvalValidationTests -v`
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add simulink_cli/actions/matlab_eval.py tests/test_matlab_eval.py
git commit -m "feat: matlab_eval action module — FIELDS, ERRORS, validate()"
```

---

### Task 3: Action module — `matlab_eval.py` execute()

**Files:**
- Modify: `simulink_cli/actions/matlab_eval.py` (implement execute)
- Modify: `tests/test_matlab_eval.py` (append execution tests)

- [ ] **Step 1: Write failing execution tests**

Append to `tests/test_matlab_eval.py`:

```python
from unittest.mock import patch
from tests.fakes import FakeModelEngine


class FakeEvalEngine:
    """Minimal engine fake that supports evalc."""
    def __init__(self, output=""):
        self._output = output
        self.warning_log = []

    def evalc(self, code, nargout=1):
        return self._output

    def lastwarn(self, *args, **kwargs):
        raise TypeError


class MatlabEvalExecuteTests(unittest.TestCase):
    def _run(self, args, engine=None):
        if engine is None:
            engine = FakeEvalEngine(output="ans =\n    3.1416\n")
        with patch.object(matlab_eval, "safe_connect_to_session", return_value=(engine, None)):
            return matlab_eval.execute(args)

    def _default_args(self, **overrides):
        args = {"code": "pi", "session": None}
        args.update(overrides)
        return args

    def test_execute_success(self):
        result = self._run(self._default_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "matlab_eval")
        self.assertEqual(result["output"], "ans =\n    3.1416\n")
        self.assertFalse(result["truncated"])
        self.assertIsInstance(result["warnings"], list)

    def test_eval_failed_on_matlab_error(self):
        engine = FakeEvalEngine()
        engine.evalc = lambda code, nargout=1: (_ for _ in ()).throw(
            RuntimeError("Undefined function 'foo'")
        )
        result = self._run(self._default_args(code="foo"), engine=engine)
        self.assertEqual(result["error"], "eval_failed")
        self.assertIn("foo", result["message"])

    def test_eval_timeout(self):
        engine = MagicMock()
        future = MagicMock()
        future.result = MagicMock(side_effect=TimeoutError("timed out"))
        engine.evalc_async = MagicMock(return_value=future)
        engine.lastwarn = MagicMock(side_effect=TypeError)
        result = self._run(self._default_args(timeout=1), engine=engine)
        self.assertEqual(result["error"], "eval_timeout")

    def test_output_truncation(self):
        long_output = "x" * 60_000
        engine = FakeEvalEngine(output=long_output)
        result = self._run(self._default_args(), engine=engine)
        self.assertNotIn("error", result)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["total_length"], 60_000)
        self.assertEqual(len(result["output"]), 50_000)

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(matlab_eval, "safe_connect_to_session", return_value=(None, error_response)):
            result = matlab_eval.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")

    def test_empty_output(self):
        engine = FakeEvalEngine(output="")
        result = self._run(self._default_args(code="x = 1;"), engine=engine)
        self.assertNotIn("error", result)
        self.assertEqual(result["output"], "")
        self.assertFalse(result["truncated"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_matlab_eval.MatlabEvalExecuteTests -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement execute()**

Replace the `execute` stub in `simulink_cli/actions/matlab_eval.py`:

```python
def execute(args):
    """Execute matlab_eval: run arbitrary MATLAB code, return captured text."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    code = args["code"]
    timeout = args.get("timeout") or FIELDS["timeout"]["default"]

    try:
        result = matlab_transport.eval_code(eng, code, timeout=timeout)
        output = result.get("value") or ""
        warnings = result.get("warnings", [])
    except TimeoutError:
        return make_error(
            "eval_timeout",
            f"MATLAB code execution timed out after {timeout}s.",
            details={"timeout": timeout},
            suggested_fix="Increase timeout or simplify the code.",
        )
    except Exception as exc:
        return make_error(
            "eval_failed",
            f"MATLAB code execution failed: {exc}",
            details={"cause": str(exc)},
            suggested_fix="Check MATLAB code syntax and referenced variables/functions.",
        )

    truncated = len(output) > _OUTPUT_MAX_CHARS
    response = {
        "action": "matlab_eval",
        "output": output[:_OUTPUT_MAX_CHARS] if truncated else output,
        "truncated": truncated,
        "warnings": warnings,
    }
    if truncated:
        response["total_length"] = len(output)
    return response
```

Also add these imports at the top of the file (after existing imports):

```python
from simulink_cli import matlab_transport
from simulink_cli.session import safe_connect_to_session
```

- [ ] **Step 4: Run execution tests to verify they pass**

Run: `python -m unittest tests.test_matlab_eval.MatlabEvalExecuteTests -v`
Expected: 6 tests PASS

- [ ] **Step 5: Run all matlab_eval tests together**

Run: `python -m unittest tests.test_matlab_eval -v`
Expected: 15 tests PASS (2 transport + 7 validation + 6 execution)

- [ ] **Step 6: Commit**

```bash
git add simulink_cli/actions/matlab_eval.py tests/test_matlab_eval.py
git commit -m "feat: matlab_eval execute() — evalc + truncation + timeout + error handling"
```

---

### Task 4: Registry registration + schema test

**Files:**
- Modify: `simulink_cli/core.py:9-50` (import + registry entry)
- Modify: `tests/test_schema_action.py:16-21` (add to expected set)

- [ ] **Step 1: Write failing schema test**

In `tests/test_schema_action.py`, add `"matlab_eval"` to the expected set (line 20):

```python
    def test_all_actions_present_with_description_and_fields(self):
        expected = {
            "schema", "scan", "connections", "inspect", "find",
            "highlight", "list_opened", "set_param", "session",
            "model_new", "model_open", "model_save", "model_close", "model_update",
            "block_add", "block_delete", "line_add", "line_delete", "simulate",
            "matlab_eval",
        }
        self.assertEqual(set(self.schema["actions"].keys()), expected)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_schema_action.SchemaActionTests.test_all_actions_present_with_description_and_fields -v`
Expected: FAIL — `matlab_eval` not in schema

- [ ] **Step 3: Register action in core.py**

In `simulink_cli/core.py`, add import (line 18, after `line_delete`):

```python
    matlab_eval,
```

Add registry entry (line 49, after `simulate`):

```python
    "matlab_eval": matlab_eval,
```

- [ ] **Step 4: Run schema test to verify it passes**

Run: `python -m unittest tests.test_schema_action -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite to check no regressions**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add simulink_cli/core.py tests/test_schema_action.py
git commit -m "feat: register matlab_eval in action registry"
```

---

### Task 5: Docs updates for docs contract

**Files:**
- Modify: `skills/simulink_automation/SKILL.md` (Recovery Routing + Responsibility & Handoff)

This task updates the skill docs to pass `test_docs_contract.py`. The contract tests check:
1. Recovery Routing covers key error codes — add `eval_failed`, `eval_timeout`
2. Responsibility & Handoff — add `matlab_eval` to the appropriate bucket

- [ ] **Step 1: Run docs contract tests to identify what fails**

Run: `python -m unittest tests.test_docs_contract -v`

Note which tests fail (if any). The new error codes `eval_failed` and `eval_timeout` are NOT currently in the required list in `test_docs_contract.py`, so the test may still pass. The Handoff tests check for specific action names — `matlab_eval` is not in the required list yet.

If all pass, this step is about **proactive maintenance**: docs should document the new action even if the test doesn't enforce it yet.

- [ ] **Step 2: Add eval_failed and eval_timeout to Recovery Routing in SKILL.md**

Find the Recovery Routing table in `skills/simulink_automation/SKILL.md` and add entries:

```markdown
| `eval_failed` | MATLAB code error | Check code syntax, referenced variables/functions |
| `eval_timeout` | Code execution timed out | Increase timeout or simplify the code |
```

- [ ] **Step 3: Add matlab_eval to Responsibility & Handoff in SKILL.md**

Find the Responsibility & Handoff section. Add `matlab_eval` to the **Direct** handling bucket (it's a simple single-call action like `simulate`).

- [ ] **Step 4: Add eval_failed and eval_timeout to docs contract test**

In `tests/test_docs_contract.py`, find `test_skill_recovery_routing_covers_key_errors` and add to the `required_codes` list:

```python
            "eval_failed",
            "eval_timeout",
```

- [ ] **Step 5: Run docs contract tests**

Run: `python -m unittest tests.test_docs_contract -v`
Expected: ALL PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add skills/simulink_automation/SKILL.md tests/test_docs_contract.py
git commit -m "docs: add matlab_eval to skill recovery routing and handoff"
```

---

### Task 6: Final validation + squash merge

- [ ] **Step 1: Run full test suite one last time**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: ALL PASS

- [ ] **Step 2: Run layered validation**

```bash
python -m unittest tests.test_schema_action -v
python -m unittest tests.test_matlab_eval -v
python -m unittest tests.test_docs_contract -v
```

Expected: ALL PASS

- [ ] **Step 3: Smoke test CLI invocation**

```bash
python -m simulink_cli schema
```

Verify `matlab_eval` appears in the schema output with correct fields.

```bash
python -m simulink_cli --json '{"action":"matlab_eval"}'
```

Verify returns `invalid_input` error (code is required).

- [ ] **Step 4: Squash merge to main**

Follow project git workflow: squash merge feature branch into main with a single commit.
