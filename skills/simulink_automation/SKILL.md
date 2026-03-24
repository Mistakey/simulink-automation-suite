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
4. **Modify** — `set_param` with dry-run preview before any write. See Write Safety Model below.
5. **Verify** — `inspect` the target after write to confirm the change took effect.

One parameter per `set_param` invocation. Always read and understand the model before modifying.

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
| `state_write_failed` / `state_clear_failed` | Check plugin state-file permissions or pass explicit `--session` |
| `invalid_json` / `json_conflict` / `unknown_parameter` / `invalid_input` | Correct request payload per `schema`, retry |
| `find` returns empty | Broaden name pattern, try different block_type, widen scope |

## Output Discipline

- Ground claims in tool JSON output — do not hallucinate parameter values.
- Keep stdout to a single JSON payload; warnings must not leak as raw text.
- Keep outputs compact: selected model, scan root, key findings.
- Do not dump full recursive trees unless explicitly requested.
- JSON mode (`--json`) is first-class and mutually exclusive with flag-mode arguments.

## Related Docs

- Response shape examples: `reference.md`
