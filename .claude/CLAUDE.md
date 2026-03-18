# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

- Plugin: `simulink-automation-suite` (fixed name, never rename)
- Current skill: `simulink-scan` (read-only Simulink analysis via MATLAB Engine for Python)
- Second skill: `simulink-edit` (Simulink parameter modification via MATLAB Engine for Python)
- Entrypoint: `python -m simulink_cli`
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
python -m simulink_cli schema
python -m simulink_cli --json '{"action":"schema"}'
```

## Architecture

### Unified CLI package (`simulink_cli/`)

| Module | Role |
|---|---|
| `core.py` | `_ACTIONS` registry, JSON parsing, schema gen, argparse auto-build, routing, error mapping, `main()`. **Contract source of truth.** |
| `errors.py` | `make_error()` — error envelope builder. |
| `json_io.py` | `JsonArgumentParser`, `emit_json()`, `as_list()`, `project_top_level_fields()`. |
| `validation.py` | `validate_text_field()`, `_invalid_input()`, `validate_json_type()` — input hardening. |
| `session.py` | MATLAB session discovery/resolution (exact-name only), local state (`.sl_pilot_state.json`). |
| `model_helpers.py` | `resolve_scan_root_path`, `resolve_inspect_target_path` — path resolution. |

### Action modules (`simulink_cli/actions/`)

| Module | Role |
|---|---|
| `scan.py` | `scan` action: model/subsystem topology with optional hierarchy. |
| `inspect_block.py` | `inspect` action: block parameter reading with effective value resolution. |
| `connections.py` | `connections` action: port traversal, edge collection. |
| `find.py` | `find` action: block search by name/type via `find_system`. |
| `highlight.py` | `highlight` action: visual-only block highlighting. |
| `list_opened.py` | `list_opened` action: enumerate open Simulink models. |
| `set_param.py` | `set_param` action: parameter modification with dry-run and rollback. |
| `session_cmd.py` | `session` action: MATLAB session management (list/use/current/clear). |

### Request flow

`__main__.py` → `core.main()` → `_extract_json_payload()` → `parse_json_request()` or `_parse_flag_mode()` (`--json` vs flag mode, mutually exclusive) → `run_action()` → `mod.validate()` → `mod.execute()` → `emit_json()` → JSON stdout

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
5. **`--json` first-class**: mutually exclusive with flag mode; type-checked via per-action `FIELDS` dicts aggregated by `core.py`.
6. **Session matching**: exact-name only, no fuzzy.
7. **Version bump required**: distributable content changes require version bump before commit.
8. **Agent-first CLI**: predictable, defensive, machine-readable design.

## Change Synchronization

**CLI actions/arguments** → update `simulink_cli/core.py` + `simulink_cli/actions/*.py` + tests + `README.md`, `README.zh-CN.md`, `SKILL.md`, `reference.md`, `test-scenarios.md`

**Error codes** → reuse existing codes; update `simulink_cli/core.py` + docs + `test_error_contract`, `test_runtime_error_mapping`, `test_docs_contract`

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
| `test_edit_module_entrypoint` | `python -m simulink_cli` works |
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
