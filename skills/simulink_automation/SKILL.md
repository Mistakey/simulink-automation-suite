---
name: simulink-automation
description: Use when working with Simulink models — analyzing topology, inspecting parameters, modifying values, or managing model lifecycle via MATLAB Engine.
---

Unified skill for all Simulink CLI operations (read-only analysis and parameter editing).
Canonical skill name is `simulink-automation` (module path `simulink_cli` is internal only).
This skill belongs to plugin `simulink-automation-suite`.

## Prerequisites

- MATLAB Engine for Python installed in the active Python environment.
- A shared MATLAB session started via `matlab.engine.shareEngine` in MATLAB.

## Discovery

Call `schema` to get the full runtime contract (actions, fields, types, defaults, error codes):

```
python -m simulink_cli schema
python -m simulink_cli --json '{"action":"schema"}'
```

Schema output is the authoritative reference for command syntax. Do not rely on static docs for field names or types.

## Workflow Strategy

1. **Discover** — `list_opened` to see available models; `session list` if multiple MATLAB sessions exist.
2. **Quick lookup** — `inspect` with a specific target and specific param for single-value checks; `highlight` for visual location.
3. **Deep analysis** — delegate to `simulink-analyzer` agent (see Responsibility & Handoff).
4. **Modify** — `set_param` with dry-run preview before any write; `block_add` for placing new blocks; `line_add` for connecting ports; `line_delete` to remove a signal connection; `block_delete` to remove a block (also silently removes connected lines). See Write Safety Model below.
5. **Simulate** — `simulate` to run the model simulation after the modeling workflow is complete.
6. **Update** — `model_update` to compile/update diagram after structural changes.
7. **Verify** — `inspect` the target after write to confirm the change took effect.
8. **Finalize** — `model_save` then `model_close` when done.

Both single-param (`param`/`value`) and multi-param (`params` object) modes available. Always read and understand the model before modifying.

## Responsibility & Handoff

This skill and the `simulink-analyzer` agent have non-overlapping responsibilities.

### Direct Handling (this skill)

The following actions are handled directly without dispatching the agent:

| Action | Reason |
|--------|--------|
| `session` (list/current/use/clear) | Meta-query; main agent needs session context for dispatch decisions |
| `list_opened` | Meta-query; main agent needs model list for dispatch decisions |
| `schema` | Self-discovery; main agent may need the action catalog |
| `highlight` | UI side-effect; no analysis output to isolate |
| `inspect` (specific target + specific param) | Single-value response; main agent needs the value in context |
| `set_param` | Write operation; requires user interaction for safety |
| `model_new` / `model_open` / `model_save` | Write/lifecycle operations |
| `model_close` / `model_update` | Lifecycle operations; direct execution |
| `block_add` | Write operation; structural mutation |
| `line_add` | Write operation; signal routing |
| `line_delete` | Write operation; signal disconnection |
| `block_delete` | Write operation; structural removal (also removes connected lines) |
| `simulate` | Operational; runs model simulation |
| `matlab_eval` | Operational; executes arbitrary MATLAB code |

### Delegate to simulink-analyzer agent

The following actions are delegated to the analyzer agent for context isolation:

| Action | Reason |
|--------|--------|
| `scan` (any configuration) | Topology output; potentially large |
| `find` (any criteria) | Search results; potentially large |
| `connections` (any configuration) | Connection graph; potentially large |
| `inspect` (no specific param or param=All) | Full parameter list; potentially large |
| Multi-step read analysis workflows | Workflow-level context isolation |

Before dispatching, resolve session and model via direct `session current` or `list_opened`, then provide them explicitly to the agent.

### Composite Requests

When a user request involves both analysis and modification (e.g., "check the PID parameters, then set Kp to 2.0"):

1. Dispatch the `simulink-analyzer` agent for the analysis portion first.
2. Use the analysis results to execute the write workflow directly via this skill.

Always analyze before writing. Never combine analysis delegation and write execution in a single step.

## Write Safety Model

All writes go through a guarded preview-execute-verify cycle:

1. **Preview** — `set_param` defaults to `dry_run=true`. Returns `current_value`, `proposed_value`, `apply_payload`, and `rollback`.
2. **Execute** — Replay the returned `apply_payload` verbatim in JSON mode. It carries `expected_current_value` as a precondition guard.
3. **Verify** — Check the `verified` field in the response. If `false`, investigate before proceeding.
4. **Rollback** — Use the `rollback` payload from any response to restore the prior value.

If the model changed between preview and execute, `precondition_failed` is returned without writing.
If read-back fails, `verification_failed` is returned with rollback and write-state data.

For response shape examples, see `reference.md`.

## Recovery Routing

Error-driven next actions (consult `schema` for the full error code list):

| Error | Recovery |
|-------|----------|
| `engine_unavailable` | Install/configure MATLAB Engine for Python, retry |
| `no_session` | Run `matlab.engine.shareEngine` in MATLAB, retry |
| `session_required` | `session list` → `session use <name>` or pass `--session` |
| `session_not_found` | `session list` → copy exact name, retry |
| `model_required` | `list_opened` → retry with explicit `--model` |
| `model_not_found` | `list_opened` → open or create the model first |
| `block_not_found` | `scan` or `find` to locate valid block path |
| `param_not_found` | `inspect --param All` to list available parameters |
| `subsystem_not_found` | Shallow root scan → select valid subsystem |
| `inactive_parameter` | Use `--resolve-effective` or `--strict-active` |
| `precondition_failed` | Rerun dry-run to refresh, replay new `apply_payload` |
| `set_param_failed` | Inspect target/value constraints; prefer rollback if write may have occurred |
| `verification_failed` | Inspect target again or use `rollback` payload |
| `model_already_loaded` | Use a different name or close existing model |
| `model_save_failed` | Check file permissions and disk space |
| `source_not_found` | Verify library source path; use `find` to browse available library blocks |
| `block_already_exists` | Use a different destination name or inspect existing block |
| `model_dirty` | `model_save` first, or retry with `force: true` to discard changes |
| `line_already_exists` | Check existing connections with `connections`; use a different port |
| `line_not_found` | Verify src/dst block and port names with `connections`; confirm the line exists before deleting |
| `simulation_failed` | Check model for errors with `model_update`; fix unconnected ports or type mismatches, then retry |
| `update_failed` | Check model for errors (unconnected ports, type mismatches); fix with `set_param` or `line_add`, retry |
| `eval_failed` | Check MATLAB code syntax and referenced variables/functions; retry with corrected code |
| `eval_timeout` | Increase timeout or simplify the code; avoid infinite loops |
| `state_write_failed` / `state_clear_failed` | Check plugin state-file permissions or pass explicit `--session` |
| `invalid_json` / `json_conflict` / `unknown_parameter` / `invalid_input` | Correct request payload per `schema`, retry |
| `find` returns empty | Broaden name pattern, try different block_type, widen scope |

## Common Patterns

Recipes for tasks that combine multiple actions. These patterns use existing CLI capabilities — no additional tools required.

### Query Bus Selector signal list

The signal names live in the `InputSignals` parameter, which is populated only after model compilation:

1. `model_update` — compile the model diagram.
2. `inspect` with `--target MyModel/BusSel --param InputSignals` — returns the comma-separated signal list.

### Discover library block paths

Library paths vary by toolbox. `block_add` auto-loads the library root on first use, so you only need the correct path:

- Standard library: `simulink/Math Operations/Gain`, `simulink/Sources/Step`
- SPS / Simscape: `powerlib/powergui`, `spsUniversalBridgeLib/Universal Bridge`
- Some paths contain literal newlines: `simulink/Signal\nRouting/Mux`. In JSON mode use the `\n` escape.

When `source_not_found` persists after auto-load, verify the path in MATLAB documentation or via `find_system('<library>', 'Type', 'block')`.

### Read block port connections

To understand how a block is wired:

1. `connections` with the block as target — returns upstream/downstream edges with numeric port indices.
2. For port names on masked blocks, `inspect --param PortNames` or related mask parameters.

**Note**: `connections` tracks Simulink signal lines only. SPS physical connections (LConn/RConn) are not visible via `connections`, but can be created/deleted via `line_add`/`line_delete` using string port names (e.g. `"RConn1"`, `"LConn1"`).

## Known Limitations

Current CLI capability boundaries. For operations beyond these limits, use direct MATLAB Engine access or `run_matlab` (when available):

| Limitation | Impact | Workaround |
|---|---|---|
| Signal lines only in `connections` | SPS electrical topology (physical connections) not reported. | Port handle queries via MATLAB or `matlab_eval` |
| No workspace access | Cannot read/write base workspace variables or simulation results. | `evalin`/`assignin` via `matlab_eval` |

## Output Discipline

- Ground claims in tool JSON output — do not hallucinate parameter values.
- Keep stdout to a single JSON payload; warnings must not leak as raw text.
- Keep outputs compact: selected model, scan root, key findings.
- Do not dump full recursive trees unless explicitly requested.
- JSON mode (`--json`) is first-class and mutually exclusive with flag-mode arguments.

## Related Docs

- Response shape examples: `reference.md`
