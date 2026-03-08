# AGENTS.md

Agent development contract for `simulink-automation-suite` (repository maintenance guide, not an end-user manual).

## 1. Core Principles

1. Contract-First: keep CLI contracts stable before adding new capability.
2. Agent-First DX: machine-readable, predictable, recoverable behavior over interactive convenience.
3. Suite Extensibility: this is a suite architecture and may grow into multiple skills/capabilities.
4. Deterministic Outputs: ordering, clipping, and field projection must be repeatable.
5. Docs-as-Contract: code, tests, and docs must be updated together in the same change.

## 2. Project Facts and Non-Negotiables

- Plugin identity is fixed: `simulink-automation-suite`
- Currently released skill: `simulink-scan` (not the final set; additional skills are expected in the future)
- Current released module entrypoint includes: `python -m skills.simulink_scan`
- Error envelope shape is fixed: `error` / `message` / `details` / optional `suggested_fix`
- Session matching is exact-name only
- `--json` is first-class and must remain mutually exclusive with flag mode
- `simulink-scan` is read-only: no model mutation (`set_param`, add/delete blocks/lines, save changes)
- In `simulink-scan`, `highlight` is visual-only (`hilite_system`) and must not mutate model data
- New write capabilities must be exposed through separate skills/command surfaces and include dry-run, explicit confirmation, rollback strategy, and safety validation

## 3. Repository Map (Source of Truth)

- Contract parsing/routing: `skills/simulink_scan/scripts/sl_core.py`
- Read-only action runtime: `skills/simulink_scan/scripts/sl_scan.py`
- MATLAB session resolution and local state: `skills/simulink_scan/scripts/sl_session.py`
- Error helper: `skills/simulink_scan/scripts/sl_errors.py`
- Entrypoint: `skills/simulink_scan/__main__.py`
- Plugin manifest: `.claude-plugin/plugin.json`
- Marketplace manifest: `.claude-plugin/marketplace.json`
- Contract tests: `tests/`

## 4. Agent-First CLI Rules (from rewrite-your-cli-for-ai-agents)

Use the following priority model for current and future development:

1. Raw JSON Payload First
   - Keep `--json` as a first-class input path that maps directly to action/API structure.
2. Runtime Schema Introspection
   - `schema` must enable runtime self-discovery (type, required, default, enum, error codes).
3. Context Window Discipline
   - Large outputs must support response budgets: `max_blocks/max_params/max_edges + fields`.
   - Default responses should stay compact and bounded.
4. Input Hardening
   - Strictly validate control characters, reserved characters, invalid JSON, unknown fields, and type mismatches.
   - Treat agent inputs as potentially adversarial and fail fast.
5. Skills + Context Files
   - Keep `SKILL.md`, `reference.md`, and `test-scenarios.md` aligned with runtime behavior.
6. Multi-Surface Consistency
   - If MCP/extensions are added later, reuse one shared contract source (no split definitions).
7. Safety Rails
   - Current released capabilities are read-focused; any future write capability must ship with `--dry-run`, explicit confirmation, and rollback-aware operation design.

## 5. Superpowers Workflow Mode (On-Demand, Not Auto-Loaded)

### 5.1 Global Rules

- Never auto-bootstrap superpowers skills at session start.
- Suggest skills only when the task context matches; do not load without user confirmation.
- Skills are temporary workflow modes, not permanent personality overlays.
- A skill expires after its phase is complete; re-evaluate for each new phase.
- Do not let conflicting skills govern at the same time; the later confirmed one takes precedence.

### 5.2 Required Suggestion Format

When recommending a skill, always include:

1. The detected task scenario
2. Why the skill is recommended
3. A direct confirmation question
4. A clear statement that work can continue without loading the skill

### 5.3 Required Command Output Format (Windows)

When recommending an official superpowers skill, also provide this copy-paste PowerShell command:

```powershell
superpowers-codex use-skill superpowers:<skill-name>
```

If the requested skill is not available, provide:

```powershell
superpowers-codex find-skills
```

Do not output Unix-style path commands such as `~/.codex/...`.

## 6. Change Synchronization Rules (Code + Tests + Docs)

### 6.1 When changing CLI actions/arguments

- Update `sl_core.py` (parser/json/schema/routing).
- Update runtime implementation in `sl_scan.py` or `sl_session.py`.
- Update tests:
  - `tests/test_schema_action.py`
  - `tests/test_json_input_mode.py`
  - `tests/test_input_validation.py`
  - related behavior and output-control tests
- Update docs:
  - `README.md`
  - `README.zh-CN.md`
  - `skills/simulink_scan/SKILL.md`
  - `skills/simulink_scan/reference.md`
  - `skills/simulink_scan/test-scenarios.md`

### 6.2 When changing error codes or error semantics

- Reuse existing stable error codes whenever possible.
- If changes are required:
  - update error code declarations in `sl_core.py`
  - update docs for error code semantics
  - update `test_error_contract`, `test_runtime_error_mapping`, and `test_docs_contract`

### 6.3 When changing output budgets/projection

- Keep parameter semantics stable:
  - `scan`: `max_blocks`, `fields`
  - `inspect`: `max_params`, `fields`
  - `connections`: `max_edges`, `fields`
- Keep `total_*` / `truncated` behavior predictable.
- Add or update dedicated output-control tests.

## 7. Verification Gate (Definition of Done)

Minimum completion gate:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Recommended layered validation during development:

```bash
python -m unittest tests.test_schema_action -v
python -m unittest tests.test_json_input_mode tests.test_input_validation -v
python -m unittest tests.test_scan_output_controls tests.test_inspect_output_controls tests.test_connections_output_controls -v
python -m unittest tests.test_docs_contract -v
```

When manifest/release files are touched, also run:

```bash
python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v
claude plugin validate .
```

## 8. Release Rules (Mandatory Version Bump Check)

Every release must include an explicit version update. Reusing the previous release version is not allowed.

Mandatory checks:

1. `plugin.json.version` must equal `marketplace.json.plugins[0].version`
2. The new release version must be higher than the previous release version (semantic versioning)
3. Tests and `claude plugin validate .` must pass before tagging/release

Release steps and detailed checks are governed by:
`docs/release/2026-03-07-github-marketplace-release-checklist.md`

## 9. Documentation Gate

- Documentation is part of the contract; behavior changes without doc updates are incomplete.
- `tests/test_docs_contract.py` must remain green.
- Keep `README.md` and `README.zh-CN.md` semantically aligned.

## 10. Local State and Engineering Notes

- `.sl_pilot_state.json` is local runtime state and is git-ignored.
- Most tests use fakes/mocks; most validation does not require local MATLAB.
- Prefer small, reviewable, rollback-friendly change sets.
