# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

- Plugin: `simulink-automation-suite` (fixed name, never rename)
- Current skill: `simulink-scan` (read-only Simulink analysis via MATLAB Engine for Python)
- Second skill: `simulink-edit` (Simulink parameter modification via MATLAB Engine for Python)
- Entrypoint: `python -m skills.simulink_scan`
- Edit entrypoint: `python -m skills.simulink_edit`
- Version: synced in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`

## Commands

```bash
# Run all tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run single test
python -m unittest tests.test_schema_action -v

# Layered validation (recommended during development)
python -m unittest tests.test_schema_action -v
python -m unittest tests.test_json_input_mode tests.test_input_validation -v
python -m unittest tests.test_scan_output_controls tests.test_inspect_output_controls tests.test_connections_output_controls tests.test_find_output_controls -v
python -m unittest tests.test_docs_contract -v

# Manifest validation (when .claude-plugin/ or README* change)
python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v
claude plugin validate .

# Local invocation
python -m skills.simulink_scan schema
python -m skills.simulink_scan --json '{"action":"schema"}'

# simulink-edit local invocation
python -m skills.simulink_edit schema
python -m skills.simulink_edit --json '{"action":"schema"}'
```

## Architecture

### Shared modules (`skills/_shared/`)

| Module | Role |
|---|---|
| `errors.py` | `make_error()` — error envelope builder. |
| `json_io.py` | `JsonArgumentParser`, `emit_json()`, `as_list()`, `project_top_level_fields()`. |
| `validation.py` | `validate_text_field()`, `_invalid_input()`, `validate_json_type()` — input hardening. |
| `session.py` | MATLAB session discovery/resolution (exact-name only), local state (`.sl_pilot_state.json`). |

### Source modules (`skills/simulink_scan/scripts/`)

| Module | Role |
|---|---|
| `sl_core.py` | CLI parser, JSON request parsing, schema builder, action routing. **Contract source of truth.** |
| `sl_actions.py` | Read-only actions: `scan`, `inspect`, `highlight`, `list_opened`. |
| `sl_connections.py` | `connections` action: port traversal, edge collection. |
| `sl_find.py` | `find` action: block search by name/type via `find_system`. |

### simulink-edit modules (`skills/simulink_edit/scripts/`)

| Module | Role |
|---|---|
| `sl_core.py` | CLI parser, JSON request parsing, schema builder, action routing, input validation, error mapping. |
| `sl_set_param.py` | `set_param` implementation: dry-run, execute, rollback, read-back verification. |

### Request flow

`__main__.py` → `sl_core.main()` → `build_parser()` → `parse_request_args()` (`--json` or flag mode, mutually exclusive) → `validate_args()` → `run_action()` → JSON stdout

### Contract docs (shipped with plugin)

- `skills/simulink_scan/SKILL.md` — agent-facing skill instructions
- `skills/simulink_scan/reference.md` — deep reference with recovery matrix
- `skills/simulink_scan/test-scenarios.md` — validation scenarios
- `skills/simulink_edit/SKILL.md` — agent-facing skill instructions
- `skills/simulink_edit/reference.md` — deep reference with recovery matrix
- `skills/simulink_edit/test-scenarios.md` — validation scenarios

## Core Rules

1. **Read-only**: `simulink-scan` never mutates models. `highlight` is visual-only (`hilite_system`).
2. **Write safety**: `simulink-edit` uses `dry_run=true` by default, rollback in every response, read-back verification on execute.
3. **Docs-as-Contract**: code + tests + docs updated together. `test_docs_contract.py` enforces.
4. **Stable error envelope**: `{error, message, details, suggested_fix?}` — shape is fixed.
5. **`--json` first-class**: mutually exclusive with flag mode; type-checked via `_JSON_FIELD_TYPES` in `sl_core.py`.
6. **Session matching**: exact-name only, no fuzzy.
7. **Version bump required**: distributable content changes require version bump before commit.
8. **Agent-first CLI**: predictable, defensive, machine-readable design.

## Change Synchronization

**CLI actions/arguments** → update `sl_core.py` + `sl_actions.py`/`sl_connections.py`/`sl_find.py` + tests + `README.md`, `README.zh-CN.md`, `SKILL.md`, `reference.md`, `test-scenarios.md`

**Error codes** → reuse existing codes; update `sl_core.py` + docs + `test_error_contract`, `test_runtime_error_mapping`, `test_docs_contract`

**Output budgets** → keep `scan`→`max_blocks,fields`, `inspect`→`max_params,fields`, `connections`→`max_edges,fields`, `find`→`max_results,fields` semantics stable; update output-control tests

## Test Map

| Test | Covers |
|---|---|
| `test_schema_action` | Schema contract shape |
| `test_json_input_mode`, `test_input_validation` | JSON parsing, type checking, unknown fields |
| `test_scan_output_controls`, `test_inspect_output_controls`, `test_connections_output_controls` | Clipping + field projection |
| `test_error_contract`, `test_runtime_error_mapping` | Error envelope + runtime error mapping |
| `test_scan_behavior`, `test_connections_behavior`, `test_inspect_active` | Action behavior (mocked MATLAB) |
| `test_find_behavior`, `test_find_output_controls` | find action behavior + clipping/projection |
| `test_edit_schema_action` | Edit schema contract shape |
| `test_edit_json_input_mode` | Edit JSON parsing, type checking |
| `test_edit_input_validation` | Edit field validation |
| `test_set_param_behavior` | set_param with mocked MATLAB |
| `test_set_param_dry_run` | Dry-run format, rollback payload |
| `test_edit_error_contract` | Edit error envelope + new codes |
| `test_edit_runtime_error_mapping` | MATLAB runtime → error code mapping |
| `test_edit_docs_contract` | Edit doc sections present |
| `test_edit_module_entrypoint` | `python -m skills.simulink_edit` works |
| `test_cross_skill_workflow` | Read→preview→write→verify cycle |
| `test_shared_validation` | Shared validation functions |
| `test_shared_session` | Shared session module + PLUGIN_ROOT |
| `test_session_state` | Session resolution + state file |
| `test_docs_contract` | Required doc sections present |
| `test_plugin_manifest_contract`, `test_marketplace_manifest_contract` | Manifest shape + version sync |
| `test_short_module_entrypoint` | Module entrypoint works |

## On-Demand Rules

Detailed rules in `.claude/rules/` auto-load when editing matching files:

- **`agent-first-cli.md`** — Agent-first CLI design: JSON-first, schema introspection, context window discipline, input hardening, safety rails. Read this when modifying CLI contract or adding actions.
- **`release.md`** — Version bump discipline + marketplace release checklist. Read this when releasing or committing distributable changes.

## Engineering Notes

- `.sl_pilot_state.json` is local runtime state (gitignored)
- Most tests use fakes/mocks; no local MATLAB required
- `simulink-edit` safety model: `dry_run` defaults true, rollback in every response, read-back verification
