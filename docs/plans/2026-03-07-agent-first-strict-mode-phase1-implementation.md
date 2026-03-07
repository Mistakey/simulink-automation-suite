# Agent-First Strict Mode Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the CLI deterministic and agent-safe by enforcing strict session resolution and fail-fast input validation, with stable machine-readable errors.

**Architecture:** Keep the existing command surface, but insert a strict validation layer before action execution and remove fuzzy session resolution paths. Normalize high-risk error paths to stable error codes (`invalid_input`, `session_required`, `session_not_found`) while preserving existing JSON output shape for successful responses.

**Tech Stack:** Python 3, `argparse`, `unittest`, existing `skills/simulink_scan/scripts/*` modules

---

Skill references: `@test-driven-development`, `@verification-before-completion`

### Task 1: Enforce Strict Session Selection (No Fuzzy Matching)

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_session.py`
- Test: `tests/test_session_state.py`

**Step 1: Write the failing tests**

Add tests for strict behavior in `tests/test_session_state.py`:

```python
def test_resolve_target_session_requires_explicit_when_multiple_sessions(self):
    with mock.patch.object(sl_session, "discover_sessions", return_value=["MATLAB_A", "MATLAB_B"]):
        with self.assertRaises(RuntimeError) as ctx:
            sl_session.resolve_target_session(None)
    self.assertIn("session_required", str(ctx.exception))


def test_command_session_use_rejects_non_exact_session_name(self):
    with mock.patch.object(sl_session, "discover_sessions", return_value=["MATLAB_12345"]):
        result = sl_session.command_session_use("matlab")
    self.assertEqual(result["error"], "session_not_found")
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_session_state.py" -v`  
Expected: FAIL because current implementation still allows fuzzy session matching.

**Step 3: Write minimal implementation**

In `skills/simulink_scan/scripts/sl_session.py`, replace fuzzy alias resolution with exact-only matching and strict multi-session behavior:

```python
def resolve_session_alias(query, sessions):
    if query in sessions:
        return {"status": "exact", "matched": query}
    return {"status": "missing"}


def resolve_target_session(explicit_session=None):
    sessions = discover_sessions()
    if not sessions:
        render_no_session_guide()
        raise RuntimeError("no_session")

    if explicit_session:
        if explicit_session in sessions:
            return explicit_session, sessions, "explicit"
        raise RuntimeError("session_not_found")

    if len(sessions) == 1:
        return sessions[0], sessions, "single"

    raise RuntimeError("session_required")
```

Update `command_session_use` to return:

```python
{"error": "session_not_found", "message": "...", "sessions": sessions}
```

when non-exact.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_session_state.py" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_session_state.py skills/simulink_scan/scripts/sl_session.py
git commit -m "fix(session): enforce strict exact session selection"
```

### Task 2: Add Unified Input Validation and `invalid_input`

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Create: `tests/test_input_validation.py`

**Step 1: Write the failing tests**

Create `tests/test_input_validation.py`:

```python
import unittest
from skills.simulink_scan.scripts.sl_core import validate_text_field


class InputValidationTests(unittest.TestCase):
    def test_rejects_control_chars(self):
        err = validate_text_field("target", "abc\x01")
        self.assertEqual(err["error"], "invalid_input")

    def test_rejects_reserved_chars(self):
        for value in ["a?b", "a#b", "a%b"]:
            err = validate_text_field("model", value)
            self.assertEqual(err["error"], "invalid_input")

    def test_rejects_trim_mismatch(self):
        err = validate_text_field("session", " MATLAB_1 ")
        self.assertEqual(err["error"], "invalid_input")
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_input_validation.py" -v`  
Expected: FAIL (`validate_text_field` not defined yet).

**Step 3: Write minimal implementation**

Add to `skills/simulink_scan/scripts/sl_core.py`:

```python
def validate_text_field(field_name, value, max_len=256):
    if value is None:
        return None
    text = str(value)
    if text != text.strip():
        return {"error": "invalid_input", "message": f"{field_name} has leading/trailing whitespace"}
    if len(text) > max_len:
        return {"error": "invalid_input", "message": f"{field_name} exceeds max length {max_len}"}
    if any(ord(ch) < 32 for ch in text):
        return {"error": "invalid_input", "message": f"{field_name} contains control characters"}
    if any(ch in text for ch in ("?", "#", "%")):
        return {"error": "invalid_input", "message": f"{field_name} contains reserved characters"}
    return None
```

Add `validate_args(parsed)` and call it before `run_action(parsed)`.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_input_validation.py" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_input_validation.py skills/simulink_scan/scripts/sl_core.py
git commit -m "feat(core): add fail-fast input validation for agent safety"
```

### Task 3: Normalize Error Payloads for Strict Paths

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Modify: `skills/simulink_scan/scripts/sl_session.py`
- Test: `tests/test_session_state.py`

**Step 1: Write the failing tests**

Add assertions in `tests/test_session_state.py` for machine-stable errors:

```python
self.assertEqual(result["error"], "session_not_found")
self.assertIn("message", result)
```

For runtime path, add a test that validates `sl_core` maps strict errors:

```python
self.assertEqual(payload["error"], "session_required")
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_session_state.py" -v`  
Expected: FAIL due unnormalized RuntimeError mapping.

**Step 3: Write minimal implementation**

In `sl_core.py`, map RuntimeError sentinel values:

```python
def map_runtime_error(exc):
    code = str(exc).strip()
    if code in {"session_required", "session_not_found", "no_session"}:
        return {"error": code, "message": code.replace("_", " ")}
    return {"error": "runtime_error", "message": str(exc)}
```

Use this mapper in the `except RuntimeError` branch.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_session_state.py" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_session_state.py skills/simulink_scan/scripts/sl_core.py skills/simulink_scan/scripts/sl_session.py
git commit -m "refactor(core): normalize strict-mode runtime errors"
```

### Task 4: Update Docs and Version Tag for Dev Stage

**Files:**
- Modify: `README.md`
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `.claude-plugin/plugin.json`

**Step 1: Write/update doc assertions (lightweight)**

Add a small doc consistency test note in commit checklist (manual verification):
- README says strict default behavior.
- SKILL says no fuzzy session instruction.
- version uses dev-stage suffix.

**Step 2: Run verification commands**

Run:
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `git diff -- README.md skills/simulink_scan/SKILL.md .claude-plugin/plugin.json`

Expected:
- All tests PASS
- docs reflect strict mode, no fuzzy guidance
- plugin version is dev-stage (example `1.0.0-dev.1`)

**Step 3: Write minimal doc/version updates**

README and SKILL examples should explicitly include:
- multi-session requires `--session`
- non-exact session rejected
- fail-fast behavior for invalid inputs

`.claude-plugin/plugin.json`:

```json
{
  "version": "1.0.0-dev.1"
}
```

**Step 4: Final regression run**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`  
Expected: PASS for all tests.

**Step 5: Commit**

```bash
git add README.md skills/simulink_scan/SKILL.md .claude-plugin/plugin.json
git commit -m "docs: document strict mode defaults and dev-stage version"
```

