# Unified CLI Architecture Refactoring — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace two duplicated `sl_core.py` CLI frameworks with a single registry-based `simulink_cli/` package.

**Architecture:** Each action self-registers via FIELDS/ERRORS/DESCRIPTION/validate()/execute() protocol. `core.py` provides generic JSON parsing, schema generation, argparse auto-build, routing, and error mapping. No argv intermediate layer for JSON mode.

**Tech Stack:** Python 3.10+, unittest, MATLAB Engine for Python (mocked in tests)

**Spec:** `docs/superpowers/specs/2026-03-17-unified-cli-refactoring-design.md`

---

## File Map

### Create (new files)

| File | Responsibility |
|------|---------------|
| `simulink_cli/__init__.py` | Package marker |
| `simulink_cli/__main__.py` | Entry point: `raise SystemExit(main())` |
| `simulink_cli/core.py` | _ACTIONS registry, JSON parsing, schema gen, argparse auto-build, routing, error mapping, main() |
| `simulink_cli/errors.py` | `make_error()` — copied from `skills/_shared/errors.py` |
| `simulink_cli/json_io.py` | `JsonArgumentParser`, `emit_json`, `as_list`, `project_top_level_fields` — copied from `skills/_shared/json_io.py` |
| `simulink_cli/validation.py` | `validate_text_field`, `validate_json_type` — copied from `skills/_shared/validation.py`, imports updated |
| `simulink_cli/session.py` | Session discovery/connection/state — copied from `skills/_shared/session.py`, `PLUGIN_ROOT` fixed to `parents[1]` |
| `simulink_cli/model_helpers.py` | `resolve_scan_root_path`, `resolve_inspect_target_path` — extracted from `sl_actions.py` |
| `simulink_cli/actions/__init__.py` | Package marker |
| `simulink_cli/actions/scan.py` | scan action — FIELDS + validate + execute |
| `simulink_cli/actions/highlight.py` | highlight action |
| `simulink_cli/actions/list_opened.py` | list_opened action |
| `simulink_cli/actions/inspect_block.py` | inspect action |
| `simulink_cli/actions/connections.py` | connections action |
| `simulink_cli/actions/find.py` | find action |
| `simulink_cli/actions/set_param.py` | set_param action |
| `simulink_cli/actions/session_cmd.py` | session list/use/current/clear action |

### Modify (existing files)

| File | Change |
|------|--------|
| `skills/simulink_scan/__main__.py` | Thin wrapper → `simulink_cli.core.main()` |
| `skills/simulink_edit/__main__.py` | Thin wrapper → `simulink_cli.core.main()` |
| `tests/test_*.py` (all 30 files) | Update import paths + adapt interfaces |
| `skills/simulink_scan/SKILL.md` | Update invocation to `python -m simulink_cli` |
| `skills/simulink_edit/SKILL.md` | Update invocation to `python -m simulink_cli` |
| `skills/simulink_scan/reference.md` | Update invocation paths |
| `skills/simulink_edit/reference.md` | Update invocation paths |
| `skills/simulink_scan/test-scenarios.md` | Update invocation paths |
| `skills/simulink_edit/test-scenarios.md` | Update invocation paths |
| `.claude/CLAUDE.md` | Update architecture docs, entrypoints, test map |
| `.claude/rules/agent-first-cli.md` | `_JSON_FIELD_TYPES` → per-action FIELDS |
| `.claude/rules/release.md` | Version sync checklist → `simulink_cli/core.py` |
| `.claude-plugin/plugin.json` | Keep version 2.0.0 |

### Delete (after migration)

| Path | When |
|------|------|
| `skills/simulink_scan/scripts/` | After G3 (all tests pass) |
| `skills/simulink_edit/scripts/` | After G3 |
| `skills/_shared/` | After G3 |

---

## Phase 1: Infrastructure + core.py (Gate G1)

### Task 1: Create package scaffolding

**Files:**
- Create: `simulink_cli/__init__.py`
- Create: `simulink_cli/__main__.py`
- Create: `simulink_cli/actions/__init__.py`

- [ ] **Step 1: Create directory structure**

Run: `mkdir -p simulink_cli/actions`

- [ ] **Step 2: Create `simulink_cli/__init__.py`**

```python
```

(Empty file — package marker only.)

- [ ] **Step 3: Create `simulink_cli/__main__.py`**

```python
from simulink_cli.core import main

raise SystemExit(main())
```

- [ ] **Step 4: Create `simulink_cli/actions/__init__.py`**

```python
```

(Empty file — package marker only.)

- [ ] **Step 5: Verify structure**

Run: `ls -R simulink_cli/`
Expected: `__init__.py`, `__main__.py`, `actions/__init__.py`

---

### Task 2: Migrate shared utilities

**Files:**
- Create: `simulink_cli/errors.py` (from `skills/_shared/errors.py`)
- Create: `simulink_cli/json_io.py` (from `skills/_shared/json_io.py`)
- Create: `simulink_cli/validation.py` (from `skills/_shared/validation.py`)
- Create: `simulink_cli/session.py` (from `skills/_shared/session.py`)

- [ ] **Step 1: Copy `errors.py` as-is**

```python
def make_error(code, message, details=None, suggested_fix=None):
    payload = {
        "error": str(code),
        "message": str(message),
        "details": details if isinstance(details, dict) else {},
    }
    if suggested_fix:
        payload["suggested_fix"] = str(suggested_fix)
    return payload
```

- [ ] **Step 2: Copy `json_io.py` as-is**

```python
import argparse
import json


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def emit_json(payload):
    print(json.dumps(payload, ensure_ascii=True, default=str))


def as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def project_top_level_fields(payload, fields):
    if not isinstance(fields, list) or not fields:
        return payload
    return {key: value for key, value in payload.items() if key in fields}
```

- [ ] **Step 3: Copy `validation.py` — update import path**

```python
from simulink_cli.errors import make_error


def _invalid_input(field_name, message):
    return make_error(
        "invalid_input",
        f"Field '{field_name}' {message}.",
        details={"field": field_name},
    )


def validate_text_field(field_name, value, max_len=256):
    if value is None:
        return None
    text = str(value)
    if not text:
        return _invalid_input(field_name, "must not be empty")
    if text != text.strip():
        return _invalid_input(field_name, "has leading/trailing whitespace")
    if len(text) > max_len:
        return _invalid_input(field_name, f"exceeds max length {max_len}")
    if any(ord(char) < 32 for char in text):
        return _invalid_input(field_name, "contains control characters")
    if any(char in text for char in ("?", "#", "%")):
        return _invalid_input(field_name, "contains reserved characters")
    return None


def validate_json_type(action, field_name, value, field_meta):
    if value is None:
        return
    field_type = field_meta.get("type")
    if field_type == "boolean" and not isinstance(value, bool):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be boolean"
        )
    if field_type == "string" and not isinstance(value, str):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be string"
        )
    if field_type == "integer" and not isinstance(value, int):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be integer"
        )
    if field_type == "array":
        if not isinstance(value, list):
            raise ValueError(
                f"invalid_json: field '{field_name}' for action '{action}' must be an array"
            )
        if field_meta.get("items") == "string" and not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError(
                f"invalid_json: field '{field_name}' for action '{action}' must be an array of strings"
            )
```

- [ ] **Step 4: Copy `session.py` — update import path + fix PLUGIN_ROOT**

Key change: `PLUGIN_ROOT = Path(__file__).resolve().parents[1]` (was `parents[2]`)

Also update:
- `from skills._shared.json_io import as_list` → `from simulink_cli.json_io import as_list`
- `from skills._shared.errors import make_error` → `from simulink_cli.errors import make_error`

Rest of the file (203 lines) copied as-is.

- [ ] **Step 5: Verify imports work**

Run: `python -c "from simulink_cli.errors import make_error; from simulink_cli.json_io import emit_json; from simulink_cli.validation import validate_text_field; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add simulink_cli/
git commit -m "feat(cli): scaffold simulink_cli package with shared utilities"
```

---

### Task 3: Extract model_helpers.py

**Files:**
- Create: `simulink_cli/model_helpers.py`
- Read: `skills/simulink_scan/scripts/sl_actions.py` (extract `resolve_scan_root_path`, `resolve_inspect_target_path`, `_ensure_model_loaded`)

- [ ] **Step 1: Identify functions to extract**

Read `skills/simulink_scan/scripts/sl_actions.py` and locate:
- `resolve_scan_root_path(eng, model_name, subsystem_path)` — resolves model+subsystem to full block path
- `resolve_inspect_target_path(eng, target, model_name)` — resolves inspect target path

Note: There is no `_ensure_model_loaded` function — model loading is handled inline within `resolve_scan_root_path`.

- [ ] **Step 2: Create `simulink_cli/model_helpers.py`**

Copy the 2 functions from `sl_actions.py`. Update imports:
- `from skills._shared.errors import make_error` → `from simulink_cli.errors import make_error`
- `from skills._shared.json_io import as_list` → `from simulink_cli.json_io import as_list`

- [ ] **Step 3: Verify import works**

Run: `python -c "from simulink_cli.model_helpers import resolve_scan_root_path; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add simulink_cli/model_helpers.py
git commit -m "feat(cli): extract model resolution helpers to model_helpers.py"
```

---

### Task 4: Create core.py framework

**Files:**
- Create: `simulink_cli/core.py`

This is the central task. core.py implements:
1. `_ACTIONS` registry dict (initially empty — populated in Phase 2)
2. `build_schema_payload()` — aggregates from action FIELDS/ERRORS/DESCRIPTION
3. `parse_json_request(raw_payload)` — JSON direct parse, no argv round-trip
4. `build_parser()` — auto-generates argparse from action FIELDS
5. `_add_argument_from_field(parser, name, meta)` — FIELDS→argparse mapping
6. `run_action(action_name, args)` — validate + execute via registry
7. `map_value_error(exc)` — unified ValueError→error envelope
8. `map_runtime_error(exc)` — unified RuntimeError→error envelope
9. `main(argv=None)` — top-level entry point

- [ ] **Step 1: Write `simulink_cli/core.py`**

```python
import json
import sys

from simulink_cli.errors import make_error
from simulink_cli.json_io import JsonArgumentParser, emit_json
from simulink_cli.validation import validate_json_type

# -- Action registry (populated by imports below, extended in Phase 2) --------
_ACTIONS = {}


# -- Schema generation --------------------------------------------------------
def build_schema_payload():
    actions = {}
    all_errors = set()
    for name, mod in _ACTIONS.items():
        actions[name] = {
            "description": mod.DESCRIPTION,
            "fields": mod.FIELDS,
        }
        all_errors.update(mod.ERRORS)
    return {
        "version": "2.0",
        "actions": {"schema": {"description": "Return machine-readable command contract and error-code catalog.", "fields": {}}, **actions},
        "error_codes": sorted(all_errors),
    }


# -- JSON direct parsing (no argv round-trip) ---------------------------------
def parse_json_request(raw_payload):
    try:
        request = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {exc.msg}") from exc

    if not isinstance(request, dict):
        raise ValueError("invalid_json: payload must be a JSON object")

    action = request.get("action")
    if not isinstance(action, str) or not action.strip():
        raise ValueError("invalid_json: action is required")
    if action == "schema":
        return "schema", {}
    if action not in _ACTIONS:
        raise ValueError(f"invalid_json: unsupported action '{action}'")

    mod = _ACTIONS[action]
    allowed = {"action"} | set(mod.FIELDS.keys())
    for key in request:
        if key not in allowed:
            raise ValueError(
                f"unknown_parameter: field '{key}' is not supported for action '{action}'"
            )

    # Validate required fields before filling defaults
    for field_name, field_meta in mod.FIELDS.items():
        if field_meta.get("required") and field_name not in request:
            raise ValueError(
                f"invalid_json: field '{field_name}' is required for action '{action}'"
            )

    args = {}
    for field_name, field_meta in mod.FIELDS.items():
        if field_name in request:
            validate_json_type(action, field_name, request[field_name], field_meta)
            args[field_name] = request[field_name]
        else:
            args[field_name] = field_meta.get("default")

    return action, args


# -- Argparse auto-generation (flag mode) ------------------------------------
def _add_argument_from_field(parser, name, meta):
    flag = f"--{name.replace('_', '-')}"
    kwargs = {"help": meta.get("description", ""), "dest": name}
    field_type = meta.get("type", "string")
    if field_type == "boolean":
        kwargs["action"] = "store_true"
        kwargs["default"] = meta.get("default", False)
        kwargs.pop("dest")
        parser.add_argument(flag, **kwargs)
        return
    if field_type == "integer":
        kwargs["type"] = int
        kwargs["default"] = meta.get("default")
    elif field_type == "array":
        kwargs["default"] = meta.get("default")
        # Accept comma-separated string (flag mode) for array fields
    else:
        kwargs["default"] = meta.get("default", "")
    if meta.get("required"):
        kwargs["required"] = True
    if "enum" in meta:
        kwargs["choices"] = meta["enum"]
    parser.add_argument(flag, **kwargs)


def build_parser():
    parser = JsonArgumentParser(description="Simulink Automation Suite CLI")
    parser.add_argument(
        "--json",
        dest="json_payload",
        help="JSON request payload. Mutually exclusive with flag mode.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser(
        "schema", help="Return machine-readable command contract"
    )
    for name, mod in _ACTIONS.items():
        sub = subparsers.add_parser(name, help=mod.DESCRIPTION)
        for field_name, field_meta in mod.FIELDS.items():
            _add_argument_from_field(sub, field_name, field_meta)
    return parser


# -- Routing -------------------------------------------------------------------
def run_action(action_name, args):
    if action_name == "schema":
        return build_schema_payload()
    mod = _ACTIONS[action_name]
    validation_error = mod.validate(args)
    if validation_error:
        return validation_error
    return mod.execute(args)


# -- Error mapping (unified) --------------------------------------------------
def _all_error_codes():
    codes = set()
    for mod in _ACTIONS.values():
        codes.update(mod.ERRORS)
    return codes


def map_value_error(exc):
    text = str(exc).strip()
    if ":" in text:
        code, message = text.split(":", 1)
        code = code.strip()
        message = message.strip()
        if code in {
            "invalid_json",
            "json_conflict",
            "unknown_parameter",
            "invalid_input",
        }:
            return make_error(code, message, details={"cause": text})
    return make_error("invalid_input", text, details={"cause": text})


def map_runtime_error(exc):
    code = str(exc).strip()
    messages = {
        "engine_unavailable": (
            "MATLAB Engine for Python is not available.",
            "Install MATLAB Engine for Python, then retry.",
        ),
        "no_session": (
            "No shared MATLAB session found.",
            "Run matlab.engine.shareEngine in MATLAB, then retry.",
        ),
        "session_required": (
            "Multiple MATLAB sessions found. Specify which session to use.",
            "Run schema or session list to discover sessions, then pass --session.",
        ),
        "session_not_found": (
            "Specified session not found.",
            "Check session name with session list, then retry.",
        ),
    }
    if code in messages:
        msg, fix = messages[code]
        return make_error(code, msg, details={"cause": code}, suggested_fix=fix)
    return make_error(
        "runtime_error", str(exc), details={"cause": str(exc)}
    )


# -- Entry point ---------------------------------------------------------------
def _extract_json_payload(argv):
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    if "--json" not in argv:
        return None, argv

    json_positions = [i for i, t in enumerate(argv) if t == "--json"]
    if len(json_positions) > 1:
        raise ValueError("json_conflict: --json can only be provided once")

    idx = json_positions[0]
    if idx >= len(argv) - 1:
        raise ValueError("invalid_json: --json requires a payload")
    if len(argv) != 2 or idx != 0:
        raise ValueError(
            "json_conflict: --json cannot be mixed with flags arguments"
        )
    return argv[idx + 1], None


def _parse_flag_mode(argv):
    parser = build_parser()
    try:
        parsed = parser.parse_args(argv)
    except ValueError as exc:
        message = str(exc).strip()
        if message.startswith("unrecognized arguments:"):
            raise ValueError(f"unknown_parameter: {message}") from exc
        raise ValueError(f"invalid_input: {message}") from exc
    action_name = parsed.action
    if action_name == "schema":
        return "schema", {}
    args = {k: v for k, v in vars(parsed).items() if k not in ("action", "json_payload")}
    # Parse comma-separated fields string into list (flag mode compat)
    for field_name, field_meta in _ACTIONS[action_name].FIELDS.items():
        if field_meta.get("type") == "array" and isinstance(args.get(field_name), str):
            args[field_name] = [s.strip() for s in args[field_name].split(",") if s.strip()]
    return action_name, args


def main(argv=None):
    try:
        raw_json, remaining = _extract_json_payload(argv)
        if raw_json is not None:
            action_name, args = parse_json_request(raw_json)
        else:
            action_name, args = _parse_flag_mode(remaining)
        result = run_action(action_name, args)
        emit_json(result)
        if isinstance(result, dict) and "error" in result:
            return 1
    except ValueError as exc:
        emit_json(map_value_error(exc))
        return 1
    except RuntimeError as exc:
        emit_json(map_runtime_error(exc))
        return 1
    except Exception as exc:
        emit_json(
            make_error(
                "runtime_error",
                "Unexpected error.",
                details={"cause": str(exc)},
            )
        )
        return 1
    return 0
```

- [ ] **Step 2: Verify core.py compiles**

Run: `python -c "from simulink_cli.core import main, build_schema_payload, parse_json_request; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add simulink_cli/core.py
git commit -m "feat(cli): implement unified core.py framework with registry pattern"
```

---

### Task 5: Write core.py framework tests

**Files:**
- Create: `tests/test_core_framework.py`

- [ ] **Step 1: Write failing tests for core.py**

```python
import json
import unittest

from simulink_cli.core import (
    _ACTIONS,
    build_schema_payload,
    main,
    map_runtime_error,
    map_value_error,
    parse_json_request,
)


class _FakeAction:
    FIELDS = {
        "name": {"type": "string", "required": True, "default": None, "description": "A name"},
        "count": {"type": "integer", "required": False, "default": 10, "description": "A count"},
    }
    ERRORS = ["fake_error"]
    DESCRIPTION = "A fake action for testing"

    @staticmethod
    def validate(args):
        if not args.get("name"):
            from simulink_cli.errors import make_error
            return make_error("invalid_input", "name is required")
        return None

    @staticmethod
    def execute(args):
        return {"action": "fake", "name": args["name"], "count": args.get("count", 10)}


class CoreSchemaTests(unittest.TestCase):
    def setUp(self):
        _ACTIONS["fake"] = _FakeAction
        self.addCleanup(lambda: _ACTIONS.pop("fake", None))

    def test_schema_includes_registered_action(self):
        schema = build_schema_payload()
        self.assertIn("fake", schema["actions"])
        self.assertEqual(schema["actions"]["fake"]["description"], "A fake action for testing")

    def test_schema_includes_schema_action(self):
        schema = build_schema_payload()
        self.assertIn("schema", schema["actions"])

    def test_schema_aggregates_error_codes(self):
        schema = build_schema_payload()
        self.assertIn("fake_error", schema["error_codes"])

    def test_schema_version(self):
        schema = build_schema_payload()
        self.assertEqual(schema["version"], "2.0")


class CoreJsonParsingTests(unittest.TestCase):
    def setUp(self):
        _ACTIONS["fake"] = _FakeAction
        self.addCleanup(lambda: _ACTIONS.pop("fake", None))

    def test_parse_valid_json(self):
        action, args = parse_json_request('{"action":"fake","name":"test"}')
        self.assertEqual(action, "fake")
        self.assertEqual(args["name"], "test")
        self.assertEqual(args["count"], 10)  # default

    def test_parse_schema_action(self):
        action, args = parse_json_request('{"action":"schema"}')
        self.assertEqual(action, "schema")
        self.assertEqual(args, {})

    def test_reject_unknown_action(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"nonexistent"}')
        self.assertIn("unsupported action", str(ctx.exception))

    def test_reject_unknown_field(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"fake","name":"x","bogus":1}')
        self.assertIn("unknown_parameter", str(ctx.exception))

    def test_reject_type_mismatch(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"fake","name":"x","count":"notint"}')
        self.assertIn("invalid_json", str(ctx.exception))

    def test_reject_invalid_json(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request("not json")
        self.assertIn("invalid_json", str(ctx.exception))

    def test_reject_non_object(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request("[1,2,3]")
        self.assertIn("invalid_json", str(ctx.exception))

    def test_reject_missing_action(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"name":"x"}')
        self.assertIn("action is required", str(ctx.exception))


class CoreErrorMappingTests(unittest.TestCase):
    def test_map_value_error_invalid_json(self):
        result = map_value_error(ValueError("invalid_json: bad stuff"))
        self.assertEqual(result["error"], "invalid_json")

    def test_map_value_error_unknown_parameter(self):
        result = map_value_error(ValueError("unknown_parameter: field 'x'"))
        self.assertEqual(result["error"], "unknown_parameter")

    def test_map_value_error_fallback(self):
        result = map_value_error(ValueError("something random"))
        self.assertEqual(result["error"], "invalid_input")

    def test_map_runtime_error_known(self):
        result = map_runtime_error(RuntimeError("no_session"))
        self.assertEqual(result["error"], "no_session")
        self.assertIn("suggested_fix", result)

    def test_map_runtime_error_unknown(self):
        result = map_runtime_error(RuntimeError("weird failure"))
        self.assertEqual(result["error"], "runtime_error")


class CoreMainTests(unittest.TestCase):
    def setUp(self):
        _ACTIONS["fake"] = _FakeAction
        self.addCleanup(lambda: _ACTIONS.pop("fake", None))

    def test_main_json_mode_success(self):
        code = main(["--json", '{"action":"fake","name":"hello"}'])
        self.assertEqual(code, 0)

    def test_main_json_mode_schema(self):
        code = main(["--json", '{"action":"schema"}'])
        self.assertEqual(code, 0)

    def test_main_json_mode_validation_error(self):
        code = main(["--json", '{"action":"fake"}'])
        self.assertEqual(code, 1)

    def test_main_invalid_json(self):
        code = main(["--json", "not json"])
        self.assertEqual(code, 1)

    def test_main_json_conflict_extra_args(self):
        code = main(["--json", '{"action":"schema"}', "extra"])
        self.assertEqual(code, 1)

    def test_main_json_conflict_json_not_first(self):
        code = main(["fake", "--json", '{"action":"schema"}'])
        self.assertEqual(code, 1)

    def test_main_json_missing_required_field(self):
        """Required field missing in JSON → invalid_json error, not invalid_input."""
        code = main(["--json", '{"action":"fake"}'])
        self.assertEqual(code, 1)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m unittest tests.test_core_framework -v`
Expected: All PASS (tests use _FakeAction registered in setUp)

- [ ] **Step 3: Commit**

```bash
git add tests/test_core_framework.py
git commit -m "test(cli): add core.py framework tests with fake action"
```

---

### Gate G1 Review

**Trigger:** Tasks 1-5 complete, core framework tests pass.

**Review scope:** `simulink_cli/core.py`, `simulink_cli/errors.py`, `simulink_cli/json_io.py`, `simulink_cli/validation.py`, `simulink_cli/session.py`, `simulink_cli/model_helpers.py`, `tests/test_core_framework.py`

**Review agents (parallel):**

1. **Code-reviewer** agent — review core.py for logic correctness, error handling, contract consistency
2. **Code-simplifier** agent — review for redundancy, over-complexity, readability
3. **Codex** — `codex review --uncommitted "Review the simulink_cli/ package scaffolding and core.py framework. Check: action protocol design, JSON parsing correctness, error envelope stability, import cleanliness. Report CRITICAL/HIGH/MEDIUM issues."`
4. **Contract-validator** agent — run `python -m unittest tests.test_core_framework -v`

**Consensus:** All CRITICAL/HIGH resolved before proceeding.

---

## Phase 2: Action Migration (Gate G2)

### Task 6: Migrate scan action

**Files:**
- Create: `simulink_cli/actions/scan.py`
- Read: `skills/simulink_scan/scripts/sl_actions.py` (scan portion: `get_model_structure` function)

- [ ] **Step 1: Create `simulink_cli/actions/scan.py`**

Extract the `get_model_structure()` function from `sl_actions.py`. Reorganize into the action protocol:

```python
from simulink_cli.errors import make_error
from simulink_cli.json_io import as_list, project_top_level_fields
from simulink_cli.validation import validate_text_field
from simulink_cli.model_helpers import resolve_scan_root_path
from simulink_cli.session import connect_to_session

FIELDS = {
    "model": {"type": "string", "required": False, "default": None,
              "description": "Optional specific model name from list_opened output."},
    "subsystem": {"type": "string", "required": False, "default": None,
                  "description": "Optional subsystem path under model."},
    "recursive": {"type": "boolean", "required": False, "default": False,
                  "description": "Recursively scan all nested blocks under scan root."},
    "hierarchy": {"type": "boolean", "required": False, "default": False,
                  "description": "Include hierarchy tree in output (implies recursive)."},
    "session": {"type": "string", "required": False, "default": None,
                "description": "Session override for this command."},
    "max_blocks": {"type": "integer", "required": False, "default": None,
                   "description": "Limit number of block entries returned."},
    "fields": {"type": "array", "items": "string", "required": False, "default": None,
               "description": "Projected block fields to include."},
}

ERRORS = [
    "model_required", "model_not_found", "subsystem_not_found",
    "invalid_subsystem_type", "runtime_error",
]

DESCRIPTION = "Read model or subsystem topology with optional hierarchy view."


def validate(args):
    for field in ("model", "subsystem", "session"):
        result = validate_text_field(field, args.get(field))
        if result:
            return result
    max_blocks = args.get("max_blocks")
    if max_blocks is not None and max_blocks <= 0:
        return make_error("invalid_input", "Field 'max_blocks' must be greater than zero.",
                          details={"field": "max_blocks"})
    return None


def execute(args):
    eng = connect_to_session(args.get("session"))
    # ... migrate get_model_structure() logic here ...
    # Key: call resolve_scan_root_path, then eng.find_system / eng.get_param
    # Return: {"action": "scan", "blocks": [...], "total_blocks": N, "truncated": bool}
```

The `execute()` body is the existing `get_model_structure()` function from `sl_actions.py`, with:
- `eng` parameter removed (resolved internally via `connect_to_session`)
- `model_name=` → `args.get("model")`
- `recursive=` → `args.get("recursive", False)`
- etc.
- `fields` parsing (comma-split) already handled by core.py for JSON mode; flag mode compat in core.py

- [ ] **Step 2: Register scan in core.py**

Add to `simulink_cli/core.py` top section:
```python
from simulink_cli.actions import scan
# ... in _ACTIONS dict:
_ACTIONS = {
    "scan": scan,
}
```

- [ ] **Step 3: Verify scan action loads**

Run: `python -c "from simulink_cli.core import _ACTIONS; print(list(_ACTIONS.keys()))"`
Expected: `['scan']`

- [ ] **Step 4: Commit**

```bash
git add simulink_cli/actions/scan.py simulink_cli/core.py
git commit -m "feat(cli): migrate scan action to simulink_cli"
```

---

### Task 7: Migrate highlight + list_opened actions

**Files:**
- Create: `simulink_cli/actions/highlight.py`
- Create: `simulink_cli/actions/list_opened.py`
- Read: `skills/simulink_scan/scripts/sl_actions.py` (highlight_block, list_opened_models)

- [ ] **Step 1: Create `simulink_cli/actions/highlight.py`**

Extract `highlight_block()` from `sl_actions.py`. Protocol:
- FIELDS: `target` (required string), `session` (optional string)
- ERRORS: `["block_not_found", "runtime_error"]`
- DESCRIPTION: `"Highlight a target block in Simulink UI."`
- validate: `validate_text_field` on target and session
- execute: `connect_to_session` then `eng.hilite_system(target)`

- [ ] **Step 2: Create `simulink_cli/actions/list_opened.py`**

Extract `list_opened_models()` from `sl_actions.py`. Protocol:
- FIELDS: `session` (optional string)
- ERRORS: `["runtime_error"]`
- DESCRIPTION: `"List currently opened Simulink models."`
- validate: `validate_text_field` on session
- execute: `connect_to_session` then `eng.find_system(type='block_diagram')`

- [ ] **Step 3: Register in core.py _ACTIONS**

Add `highlight` and `list_opened` to `_ACTIONS` dict.

- [ ] **Step 4: Commit**

```bash
git add simulink_cli/actions/highlight.py simulink_cli/actions/list_opened.py simulink_cli/core.py
git commit -m "feat(cli): migrate highlight and list_opened actions"
```

---

### Task 8: Migrate inspect action

**Files:**
- Create: `simulink_cli/actions/inspect_block.py`
- Read: `skills/simulink_scan/scripts/sl_actions.py` (inspect_block function)

- [ ] **Step 1: Create `simulink_cli/actions/inspect_block.py`**

Extract `inspect_block()` from `sl_actions.py`. Protocol mirrors scan `_JSON_FIELD_TYPES["inspect"]`:
- FIELDS: model, target (required), param (default "All"), active_only, strict_active, resolve_effective, summary, session, max_params, fields
- ERRORS: `["model_not_found", "block_not_found", "inactive_parameter", "runtime_error"]`
- validate: text validation on model, target, session; max_params > 0 check
- execute: full `inspect_block()` logic with model resolution

- [ ] **Step 2: Register in core.py**
- [ ] **Step 3: Commit**

---

### Task 9: Migrate connections action

**Files:**
- Create: `simulink_cli/actions/connections.py`
- Read: `skills/simulink_scan/scripts/sl_connections.py` (get_block_connections)

- [ ] **Step 1: Create `simulink_cli/actions/connections.py`**

Copy `get_block_connections()` logic. **Important:** `sl_connections.py` imports `resolve_inspect_target_path` from `sl_actions.py` — update to `from simulink_cli.model_helpers import resolve_inspect_target_path`. FIELDS mirrors `_JSON_FIELD_TYPES["connections"]`:
- FIELDS: model, target (required), direction (default "both", enum), depth (default 1), detail (default "summary", enum), include_handles, max_edges, fields, session
- ERRORS: `["model_not_found", "block_not_found", "runtime_error"]`
- validate: text validation + depth > 0, max_edges > 0, direction enum, detail enum

- [ ] **Step 2: Register in core.py**
- [ ] **Step 3: Commit**

---

### Task 10: Migrate find action

**Files:**
- Create: `simulink_cli/actions/find.py`
- Read: `skills/simulink_scan/scripts/sl_find.py` (find_blocks)

- [ ] **Step 1: Create `simulink_cli/actions/find.py`**

Copy `find_blocks()` logic. FIELDS mirrors `_JSON_FIELD_TYPES["find"]`:
- FIELDS: model, subsystem, name, block_type, session, max_results (default 200), fields
- ERRORS: `["model_not_found", "runtime_error"]`
- validate: text fields + at least one of name/block_type required + max_results > 0

- [ ] **Step 2: Register in core.py**
- [ ] **Step 3: Commit**

---

### Task 11: Migrate set_param action

**Files:**
- Create: `simulink_cli/actions/set_param.py`
- Read: `skills/simulink_edit/scripts/sl_set_param.py`

- [ ] **Step 1: Create `simulink_cli/actions/set_param.py`**

Copy `set_param()` logic. FIELDS mirrors edit's `_JSON_FIELD_TYPES["set_param"]`:
- FIELDS: target (required), param (required), value (required), dry_run (default true), model, session
- ERRORS: `["block_not_found", "param_not_found", "set_param_failed", "model_not_found", "runtime_error"]`
- validate: text fields on target/param/value/model/session; required checks for target/param/value
- execute: `connect_to_session` then existing `set_param()` logic with dry_run/rollback

- [ ] **Step 2: Register in core.py**
- [ ] **Step 3: Commit**

---

### Task 12: Migrate session_cmd action

**Files:**
- Create: `simulink_cli/actions/session_cmd.py`
- Read: `skills/simulink_scan/scripts/sl_core.py` (session routing in run_action, lines 727-740)
- Read: `skills/_shared/session.py` (command_session_* functions)

- [ ] **Step 1: Create `simulink_cli/actions/session_cmd.py`**

```python
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_text_field
from simulink_cli.session import (
    command_session_clear,
    command_session_current,
    command_session_list,
    command_session_use,
)

_SESSION_ACTIONS = {"list", "use", "current", "clear"}

FIELDS = {
    "session_action": {
        "type": "string", "required": True, "default": None,
        "enum": ["list", "use", "current", "clear"],
        "description": "Session management operation.",
    },
    "name": {
        "type": "string", "required": False, "default": None,
        "description": "Session name, required when session_action=use.",
    },
}

ERRORS = [
    "no_session", "session_not_found", "session_required",
    "state_write_failed", "state_clear_failed",
]

DESCRIPTION = "Manage active MATLAB shared session selection."


def validate(args):
    sa = args.get("session_action")
    if not isinstance(sa, str) or sa not in _SESSION_ACTIONS:
        return make_error(
            "invalid_input",
            f"session_action must be one of {sorted(_SESSION_ACTIONS)}.",
            details={"field": "session_action"},
        )
    if sa == "use":
        name = args.get("name")
        if not name:
            return make_error(
                "invalid_input",
                "Field 'name' is required when session_action=use.",
                details={"field": "name"},
            )
        result = validate_text_field("name", name)
        if result:
            return result
    elif args.get("name") is not None:
        return make_error(
            "unknown_parameter",
            "Field 'name' is only supported when session_action=use.",
            details={"field": "name"},
        )
    return None


def execute(args):
    sa = args["session_action"]
    if sa == "list":
        return command_session_list()
    if sa == "use":
        return command_session_use(args["name"])
    if sa == "current":
        return command_session_current()
    if sa == "clear":
        return command_session_clear()
    return make_error("invalid_input", f"Unsupported session_action '{sa}'.")
```

**Flag mode breaking change:** The old session syntax was `session use <name>` (positional subcommand). The new auto-generated syntax is `session --session-action use --name <name>`. This is intentional — the CLI is JSON-first, and flag mode is auto-generated from FIELDS. Update any tests that use the old positional syntax.

- [ ] **Step 2: Register in core.py**

Ensure `_ACTIONS` now contains all 8 actions: scan, highlight, list_opened, inspect, connections, find, set_param, session.

- [ ] **Step 3: Verify all actions registered**

Run: `python -c "from simulink_cli.core import _ACTIONS; print(sorted(_ACTIONS.keys()))"`
Expected: `['connections', 'find', 'highlight', 'inspect', 'list_opened', 'scan', 'session', 'set_param']`

- [ ] **Step 4: Verify schema output**

Run: `python -m simulink_cli schema`
Expected: JSON with all 9 actions (including schema), version "2.0"

- [ ] **Step 5: Commit**

```bash
git add simulink_cli/actions/session_cmd.py simulink_cli/core.py
git commit -m "feat(cli): migrate session_cmd action, all 8 actions registered"
```

---

### Gate G2 Review

**Trigger:** Tasks 6-12 complete, all actions registered, `python -m simulink_cli schema` outputs valid JSON.

**Review scope:** All `simulink_cli/actions/*.py`, updated `simulink_cli/core.py`

**Review agents (parallel):**

1. **Code-reviewer** — Business logic preservation: compare each action's execute() with original function. FIELDS match original `_JSON_FIELD_TYPES`. validate() covers all cases from original `validate_args()`.
2. **Code-simplifier** — Check for redundancy across action modules, consistent patterns, DRY validation helpers.
3. **Codex** — `codex exec -s read-only "Review simulink_cli/actions/ directory. Verify: (1) all 8 actions follow FIELDS/ERRORS/DESCRIPTION/validate/execute protocol, (2) no business logic was lost vs originals in skills/simulink_scan/scripts/ and skills/simulink_edit/scripts/, (3) imports are clean. Report CRITICAL/HIGH/MEDIUM."`
4. **Contract-validator** — `python -m simulink_cli schema` output includes all expected actions, fields, error codes.

---

## Phase 3: Test Migration (Gate G3)

### Task 13: Migrate core/schema/JSON input tests

**Files:**
- Modify: `tests/test_schema_action.py`, `tests/test_edit_schema_action.py`
- Modify: `tests/test_json_input_mode.py`, `tests/test_edit_json_input_mode.py`

- [ ] **Step 1: Update `test_schema_action.py` imports**

```python
# Old:
from skills.simulink_scan.scripts.sl_core import build_parser, parse_request_args, run_action
# New:
from simulink_cli.core import build_schema_payload, main, parse_json_request
```

Adapt tests: `run_action(parser.parse_args(["schema"]))` → `build_schema_payload()` or `main(["schema"])`

- [ ] **Step 2: Merge `test_edit_schema_action.py` into `test_schema_action.py`**

Since there's now one unified schema, merge the edit-specific schema tests. The unified schema should include both scan and edit actions. **Note:** Edit tests asserting `version == '1.0'` must be updated to `'2.0'` — this is the schema version fix from the spec. Also: `error_codes` ordering changes to alphabetical (sorted set) — update any tests asserting exact ordered list.

- [ ] **Step 3: Update JSON input mode tests**

Replace `parse_request_args(parser, ["--json", ...])` with `parse_json_request(...)` or `main(["--json", ...])`.

- [ ] **Step 4: Run updated tests**

Run: `python -m unittest tests.test_schema_action tests.test_json_input_mode -v`
Expected: All PASS

- [ ] **Step 5: Commit**

---

### Task 14: Migrate action behavior tests

**Files:**
- Modify: `tests/test_scan_behavior.py`, `tests/test_connections_behavior.py`, `tests/test_inspect_active.py`, `tests/test_find_behavior.py`, `tests/test_set_param_behavior.py`, `tests/test_set_param_dry_run.py`, `tests/test_cross_skill_workflow.py`

- [ ] **Step 1: Update imports**

Pattern for each file:
```python
# Old:
from skills.simulink_scan.scripts.sl_actions import get_model_structure
# New:
from simulink_cli.actions.scan import execute as scan_execute
```

Note: action `execute()` functions take `args` dict, not individual kwargs. Tests must be updated to pass dicts instead of kwargs. Example:

```python
# Old:
result = get_model_structure(eng, model_name="m", recursive=True)
# New:
# The execute() function calls connect_to_session internally.
# For unit tests, we mock connect_to_session and call the internal logic.
# Alternative: extract the MATLAB logic into a private function, test that.
```

**Important:** Most behavior tests create fake engines and pass them directly. The new execute() calls `connect_to_session()` internally. Two approaches:
1. Mock `connect_to_session` to return the fake engine
2. Keep internal implementation functions (e.g., `_scan_impl(eng, args)`) testable

Recommend approach 2: each action module has a public `execute(args)` and a testable `_impl(eng, **kwargs)` that the old tests can call directly.

- [ ] **Step 2: Run each test file after migration**

Run: `python -m unittest tests.test_scan_behavior tests.test_connections_behavior tests.test_inspect_active tests.test_find_behavior tests.test_set_param_behavior tests.test_set_param_dry_run tests.test_cross_skill_workflow -v`

- [ ] **Step 3: Commit**

---

### Task 15: Migrate remaining tests

**Files:**
- Modify: `tests/test_input_validation.py`, `tests/test_edit_input_validation.py`
- Modify: `tests/test_scan_output_controls.py`, `tests/test_inspect_output_controls.py`, `tests/test_connections_output_controls.py`, `tests/test_find_output_controls.py`
- Modify: `tests/test_error_contract.py`, `tests/test_edit_error_contract.py`
- Modify: `tests/test_runtime_error_mapping.py`, `tests/test_edit_runtime_error_mapping.py`
- Modify: `tests/test_shared_validation.py`, `tests/test_shared_session.py`, `tests/test_session_state.py`

- [ ] **Step 1: Update validation test imports**

`tests/test_input_validation.py`: `from simulink_cli.core import run_action` + adapt Namespace→dict
`tests/test_shared_validation.py`: `from simulink_cli.validation import validate_text_field`

- [ ] **Step 2: Update output control test imports**

These test `validate_args` + action functions with field projection. Update to use action module's `validate()` + `_impl()`.

- [ ] **Step 3: Update error contract tests**

`from simulink_cli.errors import make_error` (unchanged function, just path change)

- [ ] **Step 4: Merge runtime error mapping tests**

Since there's now one `map_runtime_error` in core.py, merge scan and edit error mapping tests into one file.

- [ ] **Step 5: Update session/shared tests**

`from simulink_cli.session import ...` (was `skills._shared.session`)
`from simulink_cli.validation import ...` (was `skills._shared.validation`)

- [ ] **Step 6: Run all migrated tests**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`

- [ ] **Step 7: Commit**

---

### Task 16: Migrate entrypoint + docs contract tests

**Files:**
- Modify: `tests/test_short_module_entrypoint.py`
- Modify: `tests/test_edit_module_entrypoint.py`
- Modify: `tests/test_docs_contract.py`, `tests/test_edit_docs_contract.py`
- Modify: `tests/test_plugin_manifest_contract.py`, `tests/test_marketplace_manifest_contract.py`

- [ ] **Step 1: Update entrypoint tests**

```python
# Old:
command = [sys.executable, "-m", "skills.simulink_scan", "schema"]
# New:
command = [sys.executable, "-m", "simulink_cli", "schema"]
```

Also add a test for the backward-compat wrapper (`python -m skills.simulink_scan schema` still works).

- [ ] **Step 2: Update docs contract tests**

Paths to SKILL.md remain in `skills/simulink_scan/` and `skills/simulink_edit/` — these tests should still pass if SKILL.md content is updated in Task 18.

- [ ] **Step 3: Run full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: All 180 tests PASS (count may change slightly due to merges/additions)

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test(cli): migrate all tests to simulink_cli import paths"
```

---

### Gate G3 Review

**Trigger:** All tests pass with `python -m unittest discover -s tests -p "test_*.py" -v`.

**Review agents (parallel):**

1. **Code-reviewer** — Verify no test logic was silently dropped. Compare test count before/after.
2. **Code-simplifier** — Look for test duplication from merged scan/edit tests.
3. **Codex** — `codex exec -s read-only "Review tests/ directory. Verify all imports use simulink_cli.*, no remaining references to skills.simulink_scan.scripts or skills.simulink_edit.scripts or skills._shared. Report any stale imports."`
4. **Contract-validator** — Run: `python -m unittest discover -s tests -p "test_*.py" -v` and verify exit code 0.

---

## Phase 4: Docs + Cleanup (Gate G4)

### Task 17: Update SKILL.md + reference.md + test-scenarios.md

**Files:**
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `skills/simulink_edit/SKILL.md`
- Modify: `skills/simulink_scan/reference.md`
- Modify: `skills/simulink_edit/reference.md`
- Modify: `skills/simulink_scan/test-scenarios.md`
- Modify: `skills/simulink_edit/test-scenarios.md`

- [ ] **Step 1: Update all `python -m skills.simulink_scan` → `python -m simulink_cli`**

Search and replace across all 6 doc files. Also update any references to `sl_core.py` or `scripts/` paths.

- [ ] **Step 2: Verify docs contract tests still pass**

Run: `python -m unittest tests.test_docs_contract tests.test_edit_docs_contract -v`

- [ ] **Step 3: Commit**

---

### Task 18: Update project rules and CLAUDE.md

**Files:**
- Modify: `.claude/CLAUDE.md`
- Modify: `.claude/rules/agent-first-cli.md`
- Modify: `.claude/rules/release.md`

- [ ] **Step 1: Update CLAUDE.md**

Update sections:
- Architecture: describe `simulink_cli/` instead of `skills/*/scripts/`
- Entrypoint: `python -m simulink_cli`
- Commands: update all invocation examples
- Module table: replace sl_core, sl_actions, etc. with core.py, actions/*
- Test map: update import paths in test descriptions

- [ ] **Step 2: Update agent-first-cli.md §2**

Replace: "`_JSON_FIELD_TYPES` in `sl_core.py` is the single source of truth"
With: "Per-action `FIELDS` dicts are the single source of truth. `core.py` aggregates them for schema output."

- [ ] **Step 3: Update release.md version sync checklist**

**Note:** `release.md` has pre-existing unstaged changes — run `git diff .claude/rules/release.md` first and reconcile before editing.

Replace: "Check: `simulink_scan/scripts/sl_core.py` and `simulink_edit/scripts/sl_core.py` must agree"
With: "Check: `simulink_cli/core.py` `build_schema_payload()` version string"

- [ ] **Step 4: Commit**

---

### Task 19: Backward compat wrappers + delete old code

**Files:**
- Modify: `skills/simulink_scan/__main__.py`
- Modify: `skills/simulink_edit/__main__.py`
- Delete: `skills/simulink_scan/scripts/`
- Delete: `skills/simulink_edit/scripts/`
- Delete: `skills/_shared/`

- [ ] **Step 1: Update backward compat wrappers**

```python
# skills/simulink_scan/__main__.py
from simulink_cli.core import main

raise SystemExit(main())
```

Same for `skills/simulink_edit/__main__.py`.

- [ ] **Step 2: Verify backward compat entry points work**

Run: `python -m skills.simulink_scan schema`
Run: `python -m skills.simulink_edit schema`
Expected: Both output valid JSON schema

- [ ] **Step 3: Delete old code**

```bash
rm -rf skills/simulink_scan/scripts/
rm -rf skills/simulink_edit/scripts/
rm -rf skills/_shared/
```

- [ ] **Step 4: Verify no stale imports remain**

Run: `grep -r "skills._shared" tests/ simulink_cli/ skills/ --include="*.py"`
Run: `grep -r "skills.simulink_scan.scripts" tests/ simulink_cli/ skills/ --include="*.py"`
Run: `grep -r "skills.simulink_edit.scripts" tests/ simulink_cli/ skills/ --include="*.py"`
Expected: No matches

- [ ] **Step 5: Run full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(cli): delete old scripts/ and _shared/ directories"
```

---

### Task 20: Final validation

**Files:**
- Verify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

- [ ] **Step 1: Run manifest contract tests**

Run: `python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v`
Expected: PASS

- [ ] **Step 2: Run plugin validate**

Run: `claude plugin validate .`
Expected: Valid

- [ ] **Step 3: Run full test suite one final time**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: All PASS, 0 failures

- [ ] **Step 4: Verify schema output is complete**

Run: `python -m simulink_cli schema | python -m json.tool`
Expected: version "2.0", 9 actions (schema + 8 registered), all error codes

- [ ] **Step 5: Commit with version confirmation**

```bash
git add -A
git commit -m "chore(cli): unified CLI refactoring complete — all tests passing"
```

---

### Gate G4 Review

**Trigger:** Task 20 complete, all tests pass, plugin validates.

**Review agents (parallel):**

1. **Code-reviewer** — Final review of entire `simulink_cli/` package against spec.
2. **Code-simplifier** — Final pass for any remaining redundancy across the codebase.
3. **Codex** — `codex review --uncommitted "Final review of unified CLI refactoring. Verify: (1) no stale references to old paths, (2) all action modules follow consistent protocol, (3) error envelope stable, (4) schema complete, (5) CLAUDE.md accurate. Report any issues."`
4. **Contract-validator** — Run full layered validation:
   ```bash
   python -m unittest discover -s tests -p "test_*.py" -v
   claude plugin validate .
   ```

**Consensus:** All CRITICAL/HIGH resolved. User confirms completion.
