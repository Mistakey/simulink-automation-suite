# Simulink Scan Skill Reference

This file is optional deep reference for the `simulink-scan` skill.
The skill belongs to plugin `simulink-automation-suite`, which currently ships both `simulink-scan` and `simulink-edit`.

## JSON Contract

- stdout is a single machine-readable JSON payload.
- stderr is human guidance and warnings.

Error envelope:

```json
{
  "error": "<stable_code>",
  "message": "<human_readable_message>",
  "details": {},
  "suggested_fix": "<optional_next_step>"
}
```

Common error codes:
- `invalid_input`
- `invalid_json`
- `unknown_parameter`
- `json_conflict`
- `engine_unavailable`
- `no_session`
- `session_required`
- `session_not_found`
- `state_write_failed`
- `state_clear_failed`
- `model_required`
- `model_not_found`
- `subsystem_not_found`
- `invalid_subsystem_type`
- `block_not_found`
- `inactive_parameter`
- `runtime_error`

## Session Behavior

- Session matching is exact-only.
- When multiple shared sessions exist, commands that connect to MATLAB require either a previously selected active session (`session use <name>`) or an explicit `--session`.
- Unknown exact session returns `session_not_found`.
- `session use` / `session clear` may return `state_write_failed` / `state_clear_failed` when the local plugin state file is not writable.
- Session management actions:
  - `python -m simulink_cli session list`
  - `python -m simulink_cli session current`
  - `python -m simulink_cli session use MATLAB_12345`
  - `python -m simulink_cli session clear`

## JSON Input Mode

- `--json` is a first-class entrypoint.
- `--json` and flag-based action arguments are mutually exclusive.
- JSON request must be an object with `action` and action-specific fields.
- Unknown JSON fields return `unknown_parameter`.
- Wrong JSON field types or malformed payload return `invalid_json`.
- JSON mode is the canonical surface for complex strings and newlines.

Examples:
- `python -m simulink_cli --json "{\"action\":\"schema\"}"`
- `python -m simulink_cli --json "{\"action\":\"list_opened\",\"session\":\"MATLAB_12345\"}"`
- `python -m simulink_cli --json "{\"action\":\"inspect\",\"model\":\"m\",\"target\":\"m/Gain\",\"param\":\"All\",\"summary\":true,\"session\":\"MATLAB_12345\"}"`
- `python -m simulink_cli --json "{\"action\":\"inspect\",\"model\":\"m\",\"target\":\"m/Display\",\"param\":\"Description\",\"summary\":true}"`

## Schema Action

- `python -m simulink_cli schema`
- Returns machine-readable action and error-code contracts for agents.

## Scan Actions

- If multiple models are opened and `--model` is omitted, the tool returns `model_required` with candidate models.
- If no model is opened and no active model root can be resolved, `scan` and `find` return `model_not_found`.
- Shallow scan:
  - `python -m simulink_cli scan --model "<model>"`
- Recursive scan:
  - `python -m simulink_cli scan --model "<model>" --recursive`
- Subsystem scan:
  - `python -m simulink_cli scan --model "<model>" --subsystem "<subsystem>" --recursive`
- Hierarchy output:
  - `python -m simulink_cli scan --model "<model>" --hierarchy`
- Output clipping:
  - `python -m simulink_cli scan --model "<model>" --max-blocks 200 --fields "name,type"`

## Inspect Actions

- Full parameter view:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "All"`
- Active-only parameters:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "All" --active-only`
- Summary mode:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "All" --summary`
- Strict active check:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "<name>" --strict-active`
- Resolve effective value:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "<name>" --resolve-effective`
- Output clipping:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "All" --max-params 50 --fields "target,values"`

## Connections Action

- Default concise neighborhood (both directions, one hop):
  - `python -m simulink_cli connections --target "<block>"`
- Upstream-only with depth expansion:
  - `python -m simulink_cli connections --target "<block>" --direction upstream --depth 2 --detail summary`
- Port-level details:
  - `python -m simulink_cli connections --target "<block>" --detail ports`
- Line-level details with optional handles:
  - `python -m simulink_cli connections --target "<block>" --detail lines --include-handles`
- Output clipping and projection:
  - `python -m simulink_cli connections --target "<block>" --detail ports --max-edges 50 --fields "target,edges,total_edges,truncated"`
- JSON request:
  - `python -m simulink_cli --json "{\"action\":\"connections\",\"target\":\"<block>\",\"direction\":\"both\",\"depth\":1,\"detail\":\"summary\",\"max_edges\":50,\"fields\":[\"target\",\"upstream_blocks\",\"downstream_blocks\"]}"`
- Invalid target path returns `block_not_found`.

## Find Action

- Search blocks by name (case-insensitive substring match):
  - `python -m simulink_cli find --model "<model>" --name "PID"`
- Search blocks by type:
  - `python -m simulink_cli find --model "<model>" --block-type "Gain"`
- Combined search (AND semantics):
  - `python -m simulink_cli find --model "<model>" --name "Controller" --block-type "SubSystem"`
- Narrow scope to subsystem:
  - `python -m simulink_cli find --model "<model>" --subsystem "Controller" --name "PID"`
- Output clipping and projection:
  - `python -m simulink_cli find --model "<model>" --name "Gain" --max-results 50 --fields "path,type"`
- JSON request:
  - `python -m simulink_cli --json '{"action":"find","model":"<model>","name":"PID","max_results":50,"fields":["path","type"]}'`
- At least one of `--name` or `--block-type` is required; omitting both returns `invalid_input`.
- `find` uses the same `FollowLinks=on` and `LookUnderMasks=all` visibility defaults as `scan`.
- Empty results (no matches) is not an error.

## Highlight Action

- Highlight is supported as a read-only visual locator (implemented via `hilite_system`, no model mutation).
- Basic usage:
  - `python -m simulink_cli highlight --target "<block>"`
- With explicit session:
  - `python -m simulink_cli highlight --target "<block>" --session "MATLAB_12345"`
- If target path is invalid, command returns `block_not_found`.

## Recovery Matrix

| Error Code | Likely Cause | Next Command | Expected Success Signal |
|---|---|---|---|
| `engine_unavailable` | MATLAB Engine for Python is not available in active interpreter | install/configure MATLAB Engine for Python and rerun the same command | command runs without `engine_unavailable` |
| `session_required` | Multiple MATLAB shared sessions and no active/explicit target | `python -m simulink_cli session list` then either `python -m simulink_cli session use <name>` or retry with `--session` | action returns payload without `error` |
| `session_not_found` | Session name is not an exact match | `python -m simulink_cli session list` then copy exact name | action connects to requested session |
| `model_required` | Multiple opened models and no explicit model | `python -m simulink_cli list_opened` then retry with `--model` | scan/inspect returns selected model |
| `inactive_parameter` | Requested parameter is inactive under current mask config | retry with `--resolve-effective` or `--strict-active` | response includes effective mapping or explicit inactive failure |
| `param_not_found` | Requested runtime parameter is not on the target block | `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "All"` | inspect returns available parameters |
| `invalid_input` (find) | Neither name nor block_type provided | provide at least one of `--name` or `--block-type` | find returns results or empty array |
| `invalid_json` | Malformed JSON or wrong field type | validate payload using `schema`, then retry | request parses and executes |

## Troubleshooting

- If MATLAB Engine for Python is unavailable, install/configure it in the active interpreter first.
- If no shared MATLAB session is found, run `matlab.engine.shareEngine` in MATLAB.
- If `matlab.engine` import fails, install/configure MATLAB Engine for Python in the active environment.
