---
name: simulink-edit
description: Use when modifying Simulink block parameters via set_param with dry-run preview and rollback support in write workflows.
---

Use this skill for Simulink model parameter modification.
Reject read-only analysis requests — redirect to `simulink-scan`.
Canonical skill name is `simulink-edit` (module path `simulink_cli` is internal only).
This skill is one capability inside plugin `simulink-automation-suite`.

## Safety Model

- `dry_run` defaults to `true`. Always preview before applying.
- Preview returns both `apply_payload` and `rollback`. Persist both before executing.
- Replay `apply_payload` exactly. It carries `expected_current_value` for guarded execute.
- If the preview is stale, execute returns `precondition_failed` without writing.
- After each execute, verify the `verified` field confirms the write took effect.
- If read-back does not confirm the requested value, the action returns `verification_failed` and preserves rollback/write-state data for recovery.
- One parameter per invocation. No batch operations.

## Preflight

0. Ensure runtime prerequisites:
   - MATLAB Engine for Python is installed in the active Python environment.
   - MATLAB shared session is started by running `matlab.engine.shareEngine` in MATLAB.
1. Discover contract when uncertain about commands/fields:
   - `python -m simulink_cli schema`
   - JSON: `python -m simulink_cli --json "{\"action\":\"schema\"}"`
2. Use `simulink-scan` to locate and inspect target blocks before editing:
   - `python -m simulink_cli find --name "PID"` → locate block
   - `python -m simulink_cli inspect --target "<block>" --param "All"` → read current values

## Action Selection

1. Parameter modification -> `set_param`
2. Capability discovery -> `schema`

## Execution Templates

- Preview parameter change (dry-run):
  - `python -m simulink_cli set_param --target "<block>" --param "<name>" --value "<new_value>"`
  - (dry_run defaults to true — returns `apply_payload`, current/proposed values, and `rollback`)
- Execute parameter change:
  - Replay the returned `apply_payload` in JSON mode instead of reconstructing the request manually
- JSON mode (preview):
  - `python -m simulink_cli --json '{"action":"set_param","target":"<block>","param":"<name>","value":"<new_value>"}'`
- JSON mode (execute):
  - `python -m simulink_cli --json '<paste apply_payload from preview response verbatim>'`

The `value` field is always a string. MATLAB `set_param` handles type conversion internally. Pass numeric values as `"2.0"`, not `2.0`. Literal percent strings such as `"%.3f"` are valid when the target parameter expects them. JSON mode is the canonical contract surface for complex strings and newlines.

JSON mode is first-class and mutually exclusive with flag-mode action arguments.

## Recovery Routing

Error-driven next actions:

- `session_required` -> run `session list` via simulink-scan, then either `session use <name>` or retry with explicit `--session`.
- `session_not_found` -> rerun `session list`, copy exact name, retry.
- `engine_unavailable` -> install/configure MATLAB Engine for Python, retry.
- `no_session` -> run `matlab.engine.shareEngine` in MATLAB, retry.
- `block_not_found` -> run `simulink-scan find` or `scan` to locate valid block path.
- `param_not_found` -> run `simulink-scan inspect` on the target to list available parameters.
- `precondition_failed` -> rerun dry-run to refresh `expected_current_value`, then replay the new `apply_payload`.
- `set_param_failed` -> inspect target/value constraints before retrying; if write may have happened, prefer rollback or inspect first.
- `verification_failed` -> inspect the target again or use the preserved `rollback` payload to restore the prior value.
- `invalid_json` / `json_conflict` / `unknown_parameter` / `invalid_input` -> correct request payload and retry.

For full matrix and examples, read `reference.md`.

## Cross-Skill Workflow

Typical read-understand-preview-write-verify cycle:

```
simulink-scan  list_opened           → discover models
simulink-scan  scan --recursive      → understand topology
simulink-scan  find --name "PID"     → locate target block
simulink-scan  inspect               → read current parameters
simulink-edit  set_param (dry_run)   → preview proposed change
simulink-edit  replay apply_payload  → guarded execute
simulink-scan  inspect               → verify result
simulink-edit  replay rollback       → restore prior value if needed
```

## Output Discipline

- Ground claims in tool JSON output.
- Always check `verified` field after execute.
- Persist `apply_payload` and `rollback` before proceeding with further changes.

## Related Docs

- Deep reference: `reference.md`
- Validation scenarios: `test-scenarios.md`
