# Unified CLI Architecture Refactoring Design

**Date**: 2026-03-17
**Status**: Approved
**Version**: 2.0.0 (unchanged — not yet published)

## Problem

The `simulink-automation-suite` plugin has two skills (`simulink-scan`, `simulink-edit`), each maintaining an independent `sl_core.py` CLI framework. This causes:

- Duplicated CLI infrastructure (`main()`, error mapping, JSON parsing, schema building)
- Divergent implementations of similar functions (`validate_args`, `_parse_json_request`) that appear duplicated but have fundamentally different logic
- Adding a new action requires 7 scattered edits in `sl_core.py`
- Adding a new skill requires copying 300+ lines of CLI boilerplate

## Solution: Registry-Based Unified CLI (Approach C)

Create a single `simulink_cli/` package with a generic framework (`core.py`) and self-registering action modules. Each action declares its own FIELDS, ERRORS, DESCRIPTION, validate(), and execute().

## Target Architecture

```
simulink_cli/
├── __init__.py
├── __main__.py              ← raise SystemExit(main()) — primary entry point: `python -m simulink_cli`
├── core.py                  ← ~250 lines: _ACTIONS dict, JSON parsing,
│                               schema generation, argparse auto-build,
│                               routing, main(), error mapping
├── errors.py                ← make_error() (from _shared/errors.py)
├── json_io.py               ← JsonArgumentParser, emit_json, as_list,
│                               project_top_level_fields (from _shared/json_io.py)
├── validation.py            ← validate_text_field, validate_json_type
│                               + composable helpers (from _shared/validation.py)
├── session.py               ← Session discovery/connection/state management
│                               (from _shared/session.py, PLUGIN_ROOT recalculated)
├── model_helpers.py         ← resolve_scan_root_path, _ensure_model_loaded
│                               (extracted from sl_actions.py)
├── actions/
│   ├── __init__.py
│   ├── scan.py              ← scan action (~250 lines)
│   ├── highlight.py         ← highlight action (~50 lines)
│   ├── list_opened.py       ← list_opened action (~30 lines)
│   ├── inspect_block.py     ← inspect action (~200 lines)
│   ├── connections.py       ← connections action (~265 lines)
│   ├── find.py              ← find action (~90 lines)
│   ├── set_param.py         ← set_param action (~78 lines, with dry_run/rollback)
│   └── session_cmd.py       ← session list/use/current/clear (~50 lines)

skills/                      ← Entrypoint wrappers + documentation (plugin discovery unchanged)
├── simulink_scan/
│   ├── __main__.py          ← Thin wrapper → simulink_cli.core.main()
│   ├── SKILL.md             ← Updated invocation paths
│   ├── reference.md
│   └── test-scenarios.md
├── simulink_edit/
│   ├── __main__.py          ← Thin wrapper → simulink_cli.core.main()
│   ├── SKILL.md
│   ├── reference.md
│   └── test-scenarios.md
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| No shared/ sub-package | Flat in package root | Only 4 utility files, all consumed within simulink_cli/ |
| Flat actions/ directory | No sub-directories | 8 actions, most under 200 lines; cross-action helpers in model_helpers.py |
| inspect file name | `inspect_block.py` | Avoids conflict with Python builtin `inspect` |
| session command file name | `session_cmd.py` | Avoids confusion with `session.py` (infrastructure) |
| scan + highlight + list_opened | Separate files | Maintains 1-action-1-module protocol; shared helpers via model_helpers.py |
| Backward compatibility | Thin wrappers in old `__main__.py` | `python -m skills.simulink_scan` still works, redirects to simulink_cli |
| Safety boundary | SKILL.md layer, not CLI enforcement | Unified CLI exposes all actions; each SKILL.md documents only its own actions. `set_param` has `dry_run=true` default. This matches `agent-first-cli.md` §7: "Write capabilities are separate skills" — at the instruction layer, not the binary layer. |

## Action Module Protocol

Every action module exports 5 members:

```python
# Required exports per action module:

FIELDS: dict[str, dict]
# Key: field name
# Value: {"type": str, "description": str, "required"?: bool, "default"?: any}
# type enum: "string", "integer", "boolean", "array"

ERRORS: list[str]
# Error codes this action can produce

DESCRIPTION: str
# One-line description for schema output and argparse help

def validate(args: dict) -> None:
    """Validate args. Raise ValueError to reject.
    Can implement arbitrary logic including sub-field dependencies.
    Example: session_cmd.validate() enforces that 'name' is only
    allowed when session_action='use'."""

def execute(args: dict) -> dict:
    """Execute action. Return JSON-serializable dict."""
```

### Session Action Special Case

The `session` action has a sub-dispatch field `session_action` (enum: `list`, `use`, `current`, `clear`) with a dependency: `name` is required only when `session_action="use"`. This is handled entirely within `session_cmd.validate()` — the generic `parse_json_request()` in core.py does not need special-case logic. The `session_action` field is modeled as a regular required string field in FIELDS, and `session_cmd.validate()` enforces the enum constraint and the `name`-only-for-use rule.

**Call chain**: `parse_json_request()` handles only generic validation (unknown fields, required fields, type checks). Per-action `validate()` is called by `run_action()` after `parse_json_request()` returns, before `execute()`. The sequence is: `parse_json_request()` → `run_action()` → `mod.validate(args)` → `mod.execute(args)`.

### Adding a New Action

1. Create `simulink_cli/actions/new_action.py` with the 5 exports (~30-80 lines)
2. Add 2 lines to `core.py`: 1 import + 1 dict entry in `_ACTIONS`
3. Write tests and update docs

**Compared to current**: 1 new file + 2 lines vs. 1 new file + 7 scattered edits in sl_core.py.

## core.py Framework Design

### _ACTIONS Registry

```python
from simulink_cli.actions import (
    scan, highlight, list_opened, inspect_block,
    connections, find, set_param, session_cmd,
)

_ACTIONS = {
    "scan":        scan,
    "highlight":   highlight,
    "list_opened": list_opened,
    "inspect":     inspect_block,
    "connections": connections,
    "find":        find,
    "set_param":   set_param,
    "session":     session_cmd,
}
```

### JSON Direct Parsing (Eliminating argv Round-Trip)

Old flow:
```
JSON → _json_request_to_argv() → ["--model", "x", ...] → argparse → Namespace → run_action
```

New flow:
```
JSON → parse_json_request() → (action_name, args_dict) → run_action
```

`parse_json_request()` validates directly against action FIELDS: checks unknown fields, required fields, type correctness. No argparse intermediate layer for JSON mode.

### Auto-Generated argparse (Flag Mode)

`build_parser()` iterates `_ACTIONS`, reads each module's `FIELDS`, and generates argparse subparsers automatically via `_add_argument_from_field()`. No hand-written 178-line parser.

### Unified Error Mapping

`map_value_error()` and `map_runtime_error()` are unified — they check error code prefixes from all registered actions' ERRORS lists. One implementation replaces two divergent versions.

### Schema Generation

`build_schema_payload()` aggregates FIELDS, ERRORS, DESCRIPTION from all registered actions. Schema version: `"2.0"`.

## Migration Strategy

### Code Migration Map

| Source | Target | Method |
|--------|--------|--------|
| `skills/_shared/errors.py` | `simulink_cli/errors.py` | Copy as-is |
| `skills/_shared/json_io.py` | `simulink_cli/json_io.py` | Copy as-is |
| `skills/_shared/validation.py` | `simulink_cli/validation.py` | Copy + add composable helpers |
| `skills/_shared/session.py` | `simulink_cli/session.py` | Copy + fix `PLUGIN_ROOT = Path(__file__).resolve().parents[1]` (one level shallower than old `parents[2]`) |
| sl_actions.py model resolution | `simulink_cli/model_helpers.py` | Extract shared helpers |
| sl_actions.py scan portion | `simulink_cli/actions/scan.py` | Migrate |
| sl_actions.py inspect portion | `simulink_cli/actions/inspect_block.py` | Migrate |
| sl_actions.py highlight portion | `simulink_cli/actions/highlight.py` | Migrate |
| sl_actions.py list_opened portion | `simulink_cli/actions/list_opened.py` | Migrate |
| sl_connections.py | `simulink_cli/actions/connections.py` | Migrate |
| sl_find.py | `simulink_cli/actions/find.py` | Migrate |
| sl_set_param.py | `simulink_cli/actions/set_param.py` | Migrate |
| scan sl_core.py session commands | `simulink_cli/actions/session_cmd.py` | Extract |
| Both sl_core.py | `simulink_cli/core.py` | Merge + simplify |

### Test Migration

All test files require import path updates. `tests/fakes.py` (fake MATLAB engines) has no skill-path imports and requires no migration changes. Imports updated mechanically:

```python
# Old patterns:
from skills.simulink_scan.scripts.sl_core import ...
from skills.simulink_edit.scripts.sl_core import ...
from skills._shared.* import ...

# New patterns:
from simulink_cli.core import ...
from simulink_cli.actions.* import ...
from simulink_cli.errors import ...
from simulink_cli.validation import ...
from simulink_cli.session import ...
```

Interface changes:
- `validate_args(Namespace)` → `action_mod.validate(dict)`
- `parse_request_args(parser, argv)` → `parse_json_request(payload)`
- `run_action(Namespace)` → `run_action(action_name, dict)`

### Backward Compatibility

Old entry points preserved as thin wrappers (both scan and edit):
```python
# skills/simulink_scan/__main__.py
from simulink_cli.core import main
raise SystemExit(main())
```
```python
# skills/simulink_edit/__main__.py
from simulink_cli.core import main
raise SystemExit(main())
```

Note: The unified `main()` exposes all actions regardless of entry point. Safety boundary is at the SKILL.md instruction layer — simulink-scan's SKILL.md documents only read actions, simulink-edit's SKILL.md documents only write actions. This is intentional: the CLI is permissive, the skill instructions are restrictive.

### Deletion Plan

After all tests pass, delete:
- `skills/simulink_scan/scripts/` (entire directory)
- `skills/simulink_edit/scripts/` (entire directory)
- `skills/_shared/` (entire directory)

### Version

Stay at `2.0.0`. This is a pre-publish development cycle — `2.0.0` has never been released to GitHub, so no version bump is required per team agreement. Fix edit schema version `"1.0"` → `"2.0"` to match plugin major.minor.

## Agent Team & Phase Gates

### Team Members

| Role | Implementation | Responsibility |
|------|----------------|----------------|
| Implementer (main session) | Claude Opus | Execute refactoring, write code, migrate tests |
| Code-reviewer | Claude Agent (code-reviewer) | Code quality, logic correctness, contract consistency |
| Code-simplifier | Claude Agent (code-simplifier) | Code conciseness, redundancy elimination, readability |
| Codex | Bash → `codex review` / `codex exec` (gpt-5.3-codex, xhigh via config.toml) | Independent third-party review perspective |
| Contract-validator | Claude Agent (general-purpose) | Run manifest/schema/docs contract tests |

### Phase Gates

| Gate | Milestone | Review Scope |
|------|-----------|--------------|
| G1 | core.py + infrastructure ready | Framework design, protocol clarity, JSON direct parsing |
| G2 | All 8 actions migrated | Business logic preserved, FIELDS complete, interface consistency |
| G3 | All tests migrated and passing | Import correctness, coverage, interface adaptation |
| G4 | Docs + cleanup + final validation | Contract tests, plugin validate, no stale references, update `agent-first-cli.md` (`_JSON_FIELD_TYPES` → per-action FIELDS) and `release.md` (version sync checklist → `simulink_cli/core.py`) |

### Review Flow Per Gate

```
Implementation complete → Trigger Phase Gate
    │
    ├─→ [Parallel]
    │     ├─ Code-reviewer agent    → Report A (quality/logic)
    │     ├─ Code-simplifier agent  → Report B (conciseness/redundancy)
    │     └─ Codex CLI (Bash)       → Report C (independent perspective)
    │
    ├─→ Contract-validator agent    → Report D (contract checks)
    │
    ├─→ Synthesize A + B + C + D
    │     ├─ Consensus (no conflicts) → Proceed
    │     └─ Divergence → Present to user for decision
    │
    └─→ User confirms → Next phase
```

### Codex Invocation Template

Model (`gpt-5.3-codex`) and reasoning effort (`xhigh`) are configured globally in `~/.codex/config.toml` — no need to pass per-invocation.

**For reviewing uncommitted changes (after each phase):**
```bash
codex review --uncommitted "<gate-specific review prompt>"
```

**For read-only code analysis (specific review tasks):**
```bash
codex exec -s read-only "<gate-specific review prompt>"
```

### Consensus Rules

- **CRITICAL**: Any reviewer raises → must fix, re-review
- **HIGH**: 2+ reviewers agree → must fix
- **MEDIUM**: Logged, does not block gate
- **Divergence**: Conflicting conclusions → presented to user
