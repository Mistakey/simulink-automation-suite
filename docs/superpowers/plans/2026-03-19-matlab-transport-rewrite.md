# MATLAB Transport Rewrite Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a unified MATLAB transport layer and migrate the CLI actions to it so live MATLAB writes, warning handling, complex-string transport, and rollback/error contracts work reliably.

**Architecture:** `session.py` remains responsible only for session discovery and connection. New module `simulink_cli/matlab_transport.py` becomes the single runtime boundary for raw MATLAB Engine calls, `nargout` handling, warning capture, and safe argument transport. Action modules keep business semantics and JSON response shaping, but stop calling raw engine methods directly.

**Tech Stack:** Python 3.10+, `unittest`, MATLAB Engine for Python, live MATLAB smoke verification, Claude Code plugin docs

**Spec:** `docs/superpowers/specs/2026-03-19-matlab-transport-rewrite-design.md`

**Execution Note:** Run implementation in a dedicated git worktree before editing code.

---

## File Map

### Create

| File | Responsibility |
|---|---|
| `simulink_cli/matlab_transport.py` | Unified raw MATLAB Engine call boundary with `nargout`, warning capture, and safe wrappers |
| `tests/test_matlab_transport.py` | Transport-layer unit tests using engine doubles that model live MATLAB semantics |
| `tests/test_cli_stdout_contract.py` | CLI-level stdout purity tests for warning-bearing execution paths |

### Modify

| File | Responsibility of change |
|---|---|
| `simulink_cli/validation.py` | Replace one-size-fits-all string validation with field-class validation helpers |
| `simulink_cli/model_helpers.py` | Stop direct engine calls; use transport for model discovery and path verification |
| `simulink_cli/actions/list_opened.py` | Use transport-backed model discovery |
| `simulink_cli/actions/set_param.py` | Use transport for safe write path and explicit write-state contract |
| `simulink_cli/actions/inspect_block.py` | Use transport for parameter access and return `param_not_found` for missing runtime params |
| `simulink_cli/actions/scan.py` | Use transport-backed `find_system` and warning propagation |
| `simulink_cli/actions/find.py` | Use transport-backed `find_system` and warning propagation |
| `simulink_cli/actions/connections.py` | Replace direct engine reads with transport wrappers where MATLAB is touched |
| `simulink_cli/actions/highlight.py` | Use transport-backed `hilite_system` |
| `tests/fakes.py` | Add richer engine doubles that model `nargout=0`, warning capture, and complex strings |
| `tests/test_set_param_behavior.py` | Update to transport-backed execute semantics and failure cases |
| `tests/test_set_param_dry_run.py` | Update dry-run/write-state/rollback expectations |
| `tests/test_cross_skill_workflow.py` | Reflect transport-backed read→write→rollback cycle |
| `tests/test_inspect_active.py` | Change missing single-param expectation to `param_not_found` |
| `tests/test_input_validation.py` | Assert new validation matrix behavior |
| `tests/test_scan_behavior.py` | Add transport-backed warning propagation expectations |
| `tests/test_find_behavior.py` | Add transport-backed warning propagation expectations |
| `tests/test_docs_contract.py` | Align required user-doc wording with new contract |
| `tests/test_edit_docs_contract.py` | Align edit-doc contract and error-code expectations |
| `README.md` | Document transport-backed behavior, JSON-mode recommendation, warning/rollback contracts |
| `README.zh-CN.md` | Mirror English updates |
| `skills/simulink_scan/SKILL.md` | Update runtime guidance for warning-safe output and complex path JSON usage |
| `skills/simulink_scan/reference.md` | Update error semantics and JSON-mode guidance |
| `skills/simulink_scan/test-scenarios.md` | Add newline/special-char and stdout-purity scenarios |
| `skills/simulink_edit/SKILL.md` | Update write-state and rollback failure guidance |
| `skills/simulink_edit/reference.md` | Update transport/write-state contract |
| `skills/simulink_edit/test-scenarios.md` | Add execute failure/verification-failure/newline payload scenarios |
| `.claude/CLAUDE.md` | Update architecture notes, test map, and live verification expectations |

---

## Chunk 1: Transport Foundation

### Task 1: Add engine doubles and failing transport tests

**Files:**
- Modify: `tests/fakes.py`
- Create: `tests/test_matlab_transport.py`

- [ ] **Step 1: Add a double that fails if a no-output MATLAB call is made without `nargout=0`**

Add to `tests/fakes.py`:

```python
class OutputSensitiveEngine:
    def __init__(self):
        self.params = {"m/Gain::Gain": "1.5"}
        self.calls = []
        self.warning_log = []

    def get_param(self, target, param, nargout=1):
        self.calls.append(("get_param", target, param, nargout))
        if param == "Handle":
            return 1.0
        return self.params[f"{target}::{param}"]

    def set_param(self, target, param, value, nargout=1):
        self.calls.append(("set_param", target, param, value, nargout))
        if nargout != 0:
            self.params[f"{target}::{param}"] = value
            raise RuntimeError("Too many output arguments")
        self.params[f"{target}::{param}"] = value

    def find_system(self, *args, nargout=1):
        self.calls.append(("find_system", args, nargout))
        self.warning_log.append("Variant warning")
        return ["m", "m/Gain"]
```

- [ ] **Step 2: Write failing transport tests**

Create `tests/test_matlab_transport.py` with:

```python
import unittest

from tests.fakes import OutputSensitiveEngine
from simulink_cli import matlab_transport


class MatlabTransportTests(unittest.TestCase):
    def test_call_no_output_forces_nargout_zero(self):
        eng = OutputSensitiveEngine()
        matlab_transport.call_no_output(eng, "set_param", "m/Gain", "Gain", "2.0")
        self.assertIn(("set_param", "m/Gain", "Gain", "2.0", 0), eng.calls)

    def test_set_param_wrapper_returns_post_call_warning_list(self):
        eng = OutputSensitiveEngine()
        result = matlab_transport.find_system(eng, "m", "Type", "block")
        self.assertEqual(result["value"], ["m", "m/Gain"])
        self.assertEqual(result["warnings"], ["Variant warning"])

    def test_set_param_round_trips_complex_strings_unchanged(self):
        eng = OutputSensitiveEngine()
        matlab_transport.set_param(eng, "m/Sub\nSystem", "FormatString", "%.3f\nnext")
        self.assertIn(("set_param", "m/Sub\nSystem", "FormatString", "%.3f\nnext", 0), eng.calls)
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `python -m unittest tests.test_matlab_transport -v`

Expected: import failure because `simulink_cli.matlab_transport` does not exist yet.

- [ ] **Step 4: Commit only after Task 2**

Do not commit yet. The new test file intentionally depends on code that does not exist.

---

### Task 2: Implement `simulink_cli/matlab_transport.py`

**Files:**
- Create: `simulink_cli/matlab_transport.py`

- [ ] **Step 1: Create the transport result helper**

Add:

```python
def _result(value=None, warnings=None):
    return {
        "value": value,
        "warnings": list(warnings or []),
    }
```

- [ ] **Step 2: Implement generic call helpers**

Start with:

```python
def call(engine, name, *args, nargout=1):
    _reset_lastwarn(engine)
    fn = getattr(engine, name)
    try:
        value = fn(*args, nargout=nargout)
    except TypeError:
        value = fn(*args)
    warnings = _drain_warnings(engine)
    return _result(value=value, warnings=warnings)


def call_no_output(engine, name, *args):
    _reset_lastwarn(engine)
    fn = getattr(engine, name)
    try:
        fn(*args, nargout=0)
    except TypeError:
        fn(*args)
    warnings = _drain_warnings(engine)
    return _result(value=None, warnings=warnings)
```

- [ ] **Step 3: Implement warning draining**

Use a deterministic adapter that supports both richer doubles and real engine fallback. The real source of truth is MATLAB `lastwarn`, not stdout scraping:

```python
def _reset_lastwarn(engine):
    if hasattr(engine, "lastwarn"):
        try:
            engine.lastwarn("", "", nargout=0)
            return
        except TypeError:
            pass
        except Exception:
            pass


def _drain_warnings(engine):
    if hasattr(engine, "lastwarn"):
        try:
            message, warning_id = engine.lastwarn(nargout=2)
            text = str(message).strip()
            if text:
                return [text]
        except TypeError:
            pass
        except Exception:
            pass
    if hasattr(engine, "warning_log"):
        warnings = list(engine.warning_log)
        engine.warning_log.clear()
        return warnings
    return []
```

For test doubles, `warning_log` remains the fallback. For live MATLAB, `lastwarn` is the capture contract the implementation must start with.

- [ ] **Step 4: Add typed wrappers used by actions**

Add:

```python
def get_param(engine, target, param):
    return call(engine, "get_param", target, param)


def set_param(engine, target, param, value):
    return call_no_output(engine, "set_param", target, param, value)


def find_system(engine, *args):
    return call(engine, "find_system", *args)


def hilite_system(engine, target):
    return call_no_output(engine, "hilite_system", target)


def bdroot(engine):
    return call(engine, "bdroot")
```

- [ ] **Step 5: Run the transport tests**

Run: `python -m unittest tests.test_matlab_transport -v`

Expected: PASS for the initial wrapper contract.

- [ ] **Step 6: Commit the transport foundation**

```bash
git add simulink_cli/matlab_transport.py tests/test_matlab_transport.py tests/fakes.py
git commit -m "feat(cli): add MATLAB transport foundation"
```

---

### Task 3: Close the transport boundary in helper code

**Files:**
- Modify: `simulink_cli/model_helpers.py`
- Modify: `simulink_cli/actions/list_opened.py`

- [ ] **Step 1: Replace direct helper calls with transport**

Update `simulink_cli/model_helpers.py` imports:

```python
from simulink_cli import matlab_transport
```

Replace direct calls such as:

```python
eng.find_system("Type", "block_diagram")
eng.bdroot()
eng.get_param(full_path, "Handle")
eng.get_param(full_path, "BlockType")
```

with transport-backed access:

```python
matlab_transport.find_system(eng, "Type", "block_diagram")["value"]
matlab_transport.bdroot(eng)["value"]
matlab_transport.get_param(eng, full_path, "Handle")["value"]
matlab_transport.get_param(eng, full_path, "BlockType")["value"]
```

Specifically enumerate and migrate all raw MATLAB touchpoints in `model_helpers.py`:

- `get_opened_models()` -> `find_system("Type", "block_diagram")`
- `resolve_scan_root_path()` -> `bdroot()`, `get_param(..., "Handle")`, `get_param(..., "BlockType")`
- `resolve_inspect_target_path()` -> model existence check through transport-backed `get_opened_models()`

- [ ] **Step 2: Update `list_opened.py`**

Keep its public behavior unchanged, but let `get_opened_models()` be transport-backed so this action no longer bypasses the new boundary.

- [ ] **Step 3: Add a focused regression test**

Extend `tests/test_matlab_transport.py` with a helper-path regression for the no-open-model fallback:

```python
def test_bdroot_fallback_is_transport_backed(self):
    eng = OutputSensitiveEngine()
    eng.open_models = []
    eng.current_root = "m"
    result = matlab_transport.bdroot(eng)
    self.assertEqual(result["value"], "m")
```

Then add one helper-level test in `tests/test_scan_behavior.py` or a focused helper test asserting `resolve_scan_root_path()` still returns the expected model when only `bdroot()` can resolve it.

- [ ] **Step 4: Run focused tests**

Run: `python -m unittest tests.test_matlab_transport tests.test_shared_session -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add simulink_cli/model_helpers.py simulink_cli/actions/list_opened.py tests/
git commit -m "refactor(cli): route helper-level MATLAB calls through transport"
```

---

## Chunk 2: Write Path and Validation Contract

### Task 4: Lock the new write-path contract with failing tests

**Files:**
- Modify: `tests/fakes.py`
- Modify: `tests/test_set_param_behavior.py`
- Modify: `tests/test_set_param_dry_run.py`
- Modify: `tests/test_cross_skill_workflow.py`
- Modify: `tests/test_inspect_active.py`

- [ ] **Step 1: Add verification-aware doubles to `tests/fakes.py`**

Add:

```python
class VerificationMismatchEngine(OutputSensitiveEngine):
    def get_param(self, target, param, nargout=1):
        value = super().get_param(target, param, nargout=nargout)
        if param == "Gain" and value == "2.0":
            return "1.5"
        return value
```

- [ ] **Step 2: Add execute-path failure coverage**

Add to `tests/test_set_param_behavior.py`:

```python
def test_execute_failure_after_attempt_includes_rollback_and_write_state(self):
    eng = OutputSensitiveEngine()
    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        result = set_param.execute(_set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False))
    self.assertEqual(result["error"], "set_param_failed")
    self.assertEqual(result["details"]["write_state"], "attempted")
    self.assertIn("rollback", result["details"])
    self.assertEqual(result["details"]["rollback"]["target"], "m/Gain")
```

- [ ] **Step 3: Add verification-failure coverage**

Add:

```python
def test_execute_verification_failure_returns_error_not_verified_false(self):
    eng = VerificationMismatchEngine()
    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        result = set_param.execute(_set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False))
    self.assertEqual(result["error"], "set_param_failed")
    self.assertEqual(result["details"]["write_state"], "verification_failed")
```

- [ ] **Step 4: Change inspect missing-param expectation**

In `tests/test_inspect_active.py`, replace:

```python
self.assertEqual(result["error"], "unknown_parameter")
```

with:

```python
self.assertEqual(result["error"], "param_not_found")
```

- [ ] **Step 5: Run the focused tests to verify failure**

Run: `python -m unittest tests.test_set_param_behavior tests.test_set_param_dry_run tests.test_cross_skill_workflow tests.test_inspect_active -v`

Expected: FAIL because the current action code still calls raw engine methods and still returns the old inspect error code.

---

### Task 5: Replace field validation with an explicit field-class matrix

**Files:**
- Modify: `simulink_cli/validation.py`
- Modify: `tests/test_input_validation.py`

- [ ] **Step 1: Introduce separate validators**

Refactor `simulink_cli/validation.py` to expose:

```python
def validate_session_field(field_name, value, max_len=256):
    return _validate_string_field(field_name, value, max_len=max_len, reserved_chars=("?", "#", "%"))


def validate_matlab_name_field(field_name, value, max_len=256):
    return _validate_string_field(
        field_name,
        value,
        max_len=max_len,
        reserved_chars=(),
        allow_control_chars=True,
    )


def validate_matlab_payload_field(field_name, value, max_len=256):
    return _validate_string_field(
        field_name,
        value,
        max_len=max_len,
        reserved_chars=(),
        allow_control_chars=True,
    )
```

- [ ] **Step 2: Make the control-character split explicit in `_validate_string_field(...)`**

Use:

```python
def _validate_string_field(field_name, value, max_len=256, reserved_chars=(), allow_control_chars=False):
    if value is None:
        return None
    text = str(value)
    if not text:
        return _invalid_input(field_name, "must not be empty")
    if text != text.strip():
        return _invalid_input(field_name, "has leading/trailing whitespace")
    if len(text) > max_len:
        return _invalid_input(field_name, f"exceeds max length {max_len}")
    if not allow_control_chars and any(ord(char) < 32 for char in text):
        return _invalid_input(field_name, "contains control characters")
    if reserved_chars and any(char in text for char in reserved_chars):
        return _invalid_input(field_name, "contains reserved characters")
    return None
```

- [ ] **Step 3: Keep the old compatibility helpers as thin wrappers**

Use:

```python
def validate_text_field(field_name, value, max_len=256):
    return validate_session_field(field_name, value, max_len=max_len)


def validate_value_field(field_name, value, max_len=256):
    return validate_matlab_payload_field(field_name, value, max_len=max_len)
```

This keeps call sites working while the actions are migrated.

- [ ] **Step 4: Add matrix tests**

Add to `tests/test_input_validation.py`:

```python
def test_validate_matlab_name_field_allows_newline_for_target(self):
    self.assertIsNone(validate_matlab_name_field("target", "m/Sub\nSystem"))


def test_validate_session_field_still_rejects_control_characters(self):
    err = validate_session_field("session", "MATLAB_\n1")
    self.assertEqual(err["error"], "invalid_input")


def test_validate_value_field_allows_percent_and_newline(self):
    self.assertIsNone(validate_value_field("value", "%.3f\nnext"))
```

- [ ] **Step 5: Run focused validation tests**

Run: `python -m unittest tests.test_input_validation tests.test_shared_validation -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add simulink_cli/validation.py tests/test_input_validation.py
git commit -m "refactor(cli): split validation by session name and MATLAB payload semantics"
```

---

### Task 6: Migrate `set_param` and `inspect_block` to the new contracts

**Files:**
- Modify: `simulink_cli/actions/set_param.py`
- Modify: `simulink_cli/actions/inspect_block.py`

- [ ] **Step 1: Update `set_param.py` to use transport**

Replace direct engine calls with:

```python
from simulink_cli import matlab_transport

current_value = str(matlab_transport.get_param(eng, target, param)["value"])
rollback = {
    "action": "set_param",
    "target": target,
    "param": param,
    "value": current_value,
    "dry_run": False,
}
write_state = "not_attempted"
```

For execute mode:

```python
try:
    write_state = "attempted"
    matlab_transport.set_param(eng, target, param, str(value))
    observed = str(matlab_transport.get_param(eng, target, param)["value"])
except Exception as exc:
    return make_error(
        "set_param_failed",
        f"Failed to set parameter '{param}' on '{target}'.",
        details={
            "target": target,
            "param": param,
            "value": str(value),
            "write_state": write_state,
            "rollback": rollback,
            "cause": str(exc),
        },
    )
```

If `observed != str(value)`, return `set_param_failed` with `write_state = "verification_failed"` instead of a success payload with `verified = False`.

- [ ] **Step 2: Change inspect missing-param mapping**

In `simulink_cli/actions/inspect_block.py`, update the single-parameter failure branch:

```python
return make_error(
    "param_not_found",
    f"Parameter '{param_name}' is not available on target block.",
    details={"target": target_path, "param": param_name},
    suggested_fix='Run inspect with --param "All" to list available parameters.',
)
```

- [ ] **Step 3: Use relaxed MATLAB-facing validation in both actions**

`set_param.py`:

```python
for field_name in ("target", "param"):
    err = validate_matlab_name_field(field_name, args.get(field_name))
```

`inspect_block.py`:

```python
for field_name in ("model", "target"):
    error = validate_matlab_name_field(field_name, args.get(field_name))
```

Keep `session` on the stricter validator.

- [ ] **Step 4: Run focused tests**

Run: `python -m unittest tests.test_set_param_behavior tests.test_set_param_dry_run tests.test_cross_skill_workflow tests.test_inspect_active tests.test_input_validation -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add simulink_cli/actions/set_param.py simulink_cli/actions/inspect_block.py simulink_cli/validation.py tests/
git commit -m "fix(cli): migrate write path and inspect param errors to transport contract"
```

---

## Chunk 3: Read Surface, Warning Contract, and CLI Purity

### Task 7: Add failing tests for warning propagation and stdout purity

**Files:**
- Create: `tests/test_cli_stdout_contract.py`
- Modify: `tests/test_scan_behavior.py`
- Modify: `tests/test_find_behavior.py`

- [ ] **Step 1: Add action-level warning expectations**

In `tests/test_scan_behavior.py` and `tests/test_find_behavior.py`, add:

```python
self.assertIn("warnings", result)
self.assertEqual(result["warnings"], ["Variant warning"])
```

using an engine double whose `find_system` path appends to `warning_log`.

- [ ] **Step 2: Add CLI stdout contract test**

Create `tests/test_cli_stdout_contract.py`:

```python
import io
import json
import unittest
from unittest.mock import patch

from simulink_cli.core import main


class CliStdoutContractTests(unittest.TestCase):
    def test_main_emits_single_json_payload_when_action_has_warnings(self):
        buf = io.StringIO()
        eng = OutputSensitiveEngine()
        with patch("simulink_cli.actions.scan.safe_connect_to_session", return_value=(eng, None)):
            with patch("sys.stdout", buf):
                exit_code = main(["scan", "--model", "m"])
        raw = buf.getvalue()
        payload = json.loads(raw)
        self.assertEqual(exit_code, 0)
        self.assertIn("warnings", payload)
        self.assertEqual(raw.strip(), json.dumps(payload, ensure_ascii=True, default=str))
```

This test must use a concrete warning-bearing action path, not `schema`.

- [ ] **Step 3: Run the tests to verify failure**

Run: `python -m unittest tests.test_scan_behavior tests.test_find_behavior tests.test_cli_stdout_contract -v`

Expected: FAIL because read actions do not yet surface `warnings`.

---

### Task 8: Migrate read actions to transport and unify warning placement

**Files:**
- Modify: `simulink_cli/actions/scan.py`
- Modify: `simulink_cli/actions/find.py`
- Modify: `simulink_cli/actions/connections.py`
- Modify: `simulink_cli/actions/highlight.py`
- Modify: `simulink_cli/model_helpers.py`

- [ ] **Step 1: Route `scan` through transport**

Replace:

```python
blocks = as_list(eng.find_system(...))
eng.get_param(blk, "BlockType")
```

with:

```python
transport_result = matlab_transport.find_system(eng, scan_root, *search_options, "Type", "block")
blocks = as_list(transport_result["value"])
warnings = list(transport_result["warnings"])
block_type = matlab_transport.get_param(eng, blk, "BlockType")["value"]
```

Add:

```python
if warnings:
    output["warnings"] = warnings
```

- [ ] **Step 2: Route `find` through transport**

Follow the same pattern and propagate `warnings` to the top-level success payload.

- [ ] **Step 3: Route `connections` through transport wrappers**

Enumerate and migrate these direct MATLAB touchpoints:

- `_read_port_info()`:
  - `get_param(port_handle, "Parent")`
  - `get_param(port_handle, "PortNumber")`
- `_read_signal_name()`:
  - `get_param(line_handle, "Name")`
- `_collect_block_edges()`:
  - `get_param(block_path, "PortHandles")`
  - `get_param(src_port, "Line")`
  - `get_param(dst_port, "Line")`
  - `get_param(line_handle, "DstPortHandle")`
  - `get_param(line_handle, "SrcPortHandle")`

Use `matlab_transport.get_param(...)["value"]` everywhere instead of raw `eng.get_param(...)`.

- [ ] **Step 4: Route `highlight` through transport wrappers**

Replace:

```python
eng.get_param(target, "Handle")
eng.hilite_system(target, "find", nargout=0)
```

with:

```python
matlab_transport.get_param(eng, target, "Handle")["value"]
matlab_transport.call_no_output(eng, "hilite_system", target, "find")
```

Keep the JSON shape unchanged unless warning propagation adds optional `warnings` on success.

- [ ] **Step 5: Expand the CLI stdout test**

Update `tests/test_cli_stdout_contract.py` so one invocation exercises a warning-bearing path and still parses as one JSON object.

- [ ] **Step 6: Run focused tests**

Run: `python -m unittest tests.test_matlab_transport tests.test_scan_behavior tests.test_find_behavior tests.test_connections_behavior tests.test_cli_stdout_contract -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add simulink_cli/actions/scan.py simulink_cli/actions/find.py simulink_cli/actions/connections.py simulink_cli/actions/highlight.py simulink_cli/model_helpers.py tests/
git commit -m "refactor(cli): migrate read actions to transport-backed warning-safe calls"
```

---

## Chunk 4: Documentation Sync and Full Verification

### Task 9: Update docs and shipped skill contracts

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `skills/simulink_scan/reference.md`
- Modify: `skills/simulink_scan/test-scenarios.md`
- Modify: `skills/simulink_edit/SKILL.md`
- Modify: `skills/simulink_edit/reference.md`
- Modify: `skills/simulink_edit/test-scenarios.md`
- Modify: `.claude/CLAUDE.md`
- Modify: `tests/test_docs_contract.py`
- Modify: `tests/test_edit_docs_contract.py`

- [ ] **Step 1: Document the new error split**

Update docs so:

- `unknown_parameter` = invalid request field/flag only
- `param_not_found` = runtime missing parameter on a valid block

- [ ] **Step 2: Document JSON mode as the canonical path for complex strings**

Add an example like:

```bash
python -m simulink_cli --json "{\"action\":\"inspect\",\"target\":\"my_model/Line1\\nGain\",\"param\":\"Gain\"}"
```

- [ ] **Step 3: Document write-state and rollback failure semantics**

Add a short example envelope:

```json
{
  "error": "set_param_failed",
  "details": {
    "write_state": "verification_failed",
    "rollback": {
      "action": "set_param",
      "target": "m/Gain",
      "param": "Gain",
      "value": "1.5",
      "dry_run": false
    }
  }
}
```

- [ ] **Step 4: Update doc-contract tests**

Make sure docs-contract tests assert:

- JSON-mode recommendation exists
- `param_not_found` wording is present where appropriate
- clean-stdout contract is documented explicitly
- warning/rollback failure semantics are documented
- wording that treats automated tests as sufficient proof of live MATLAB compatibility is removed

- [ ] **Step 5: Run doc tests**

Run: `python -m unittest tests.test_docs_contract tests.test_edit_docs_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md README.zh-CN.md skills/ .claude/CLAUDE.md tests/test_docs_contract.py tests/test_edit_docs_contract.py
git commit -m "docs(cli): align transport rewrite contract across docs and skills"
```

---

### Task 10: Run full verification and live smoke checks

**Files:**
- Modify: none unless failures require follow-up

- [ ] **Step 1: Run the complete automated suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`

Expected: PASS.

- [ ] **Step 2: Verify schema still loads**

Run: `python -m simulink_cli schema`

Expected: JSON payload containing `set_param`, `inspect`, and unchanged top-level action list.

- [ ] **Step 3: Discover a concrete live target and baseline value**

Run these in order:

```bash
python -m simulink_cli list_opened
python -m simulink_cli scan --model "<real model>"
python -m simulink_cli find --model "<real model>" --block-type Gain
python -m simulink_cli inspect --model "<real model>" --target "<real target>" --param "All"
```

Selection rule:

- choose one opened non-library model
- choose one writable block with a single reversible parameter
- record:
  - `model`
  - `target`
  - `param`
  - current value from `inspect`
  - proposed new value

Expected: one concrete `(model, target, param, current_value, new_value)` tuple is written into the verification notes before proceeding.

- [ ] **Step 4: Run live dry-run**

Run:

```bash
python -m simulink_cli --json "{\"action\":\"set_param\",\"target\":\"<real target>\",\"param\":\"<real param>\",\"value\":\"<new value>\"}"
```

Expected:

- exit code `0`
- top-level `rollback`
- `dry_run: true`

- [ ] **Step 5: Capture the dry-run rollback payload verbatim**

Save the exact returned JSON object or at minimum the exact `rollback` object from Step 4 into the verification notes. This exact payload will be replayed in Step 7.

Expected: a concrete rollback JSON payload is available before any live write is attempted.

- [ ] **Step 6: Run live execute + verify**

Run:

```bash
python -m simulink_cli --json "{\"action\":\"set_param\",\"target\":\"<real target>\",\"param\":\"<real param>\",\"value\":\"<new value>\",\"dry_run\":false}"
```

Expected:

- exit code `0`
- no "Too many output arguments"
- `verified: true`
- top-level `rollback`

- [ ] **Step 7: Run live rollback**

Run the exact rollback payload captured in Step 5 with `--json`.

Expected:

- exit code `0`
- original value restored

- [ ] **Step 8: Run newline-containing live smoke**

Use a real `target` or `value` containing a newline, through JSON mode.

Expected:

- request parses
- transport does not corrupt the string
- stdout remains a single JSON payload

- [ ] **Step 9: Final commit if implementation required follow-up**

```bash
git status --short
```

If clean: no commit needed.

If fixes were required after verification:

```bash
git add .
git commit -m "fix(cli): resolve final verification issues in transport rewrite"
```

---

Plan complete and saved to `docs/superpowers/plans/2026-03-19-matlab-transport-rewrite.md`. Ready to execute?
