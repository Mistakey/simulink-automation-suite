# Simulink Scan Skill Reference

This file is optional deep reference for the `simulink-scan` skill.
The skill belongs to plugin `simulink-automation-suite`, which may include additional non-scan skills in future releases.

## JSON Contract

- stdout is machine-readable JSON.
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
- `model_required`
- `model_not_found`
- `subsystem_not_found`
- `invalid_subsystem_type`
- `block_not_found`
- `inactive_parameter`
- `runtime_error`

## Session Behavior

- Session matching is exact-only.
- When multiple shared sessions exist, commands that connect to MATLAB require explicit `--session`.
- Unknown exact session returns `session_not_found`.
- Session management actions:
  - `python -m skills.simulink_scan session list`
  - `python -m skills.simulink_scan session current`
  - `python -m skills.simulink_scan session use MATLAB_12345`
  - `python -m skills.simulink_scan session clear`

## JSON Input Mode

- `--json` is a first-class entrypoint.
- `--json` and flag-based action arguments are mutually exclusive.
- JSON request must be an object with `action` and action-specific fields.
- Unknown JSON fields return `unknown_parameter`.
- Wrong JSON field types or malformed payload return `invalid_json`.

Examples:
- `python -m skills.simulink_scan --json "{\"action\":\"schema\"}"`
- `python -m skills.simulink_scan --json "{\"action\":\"list_opened\",\"session\":\"MATLAB_12345\"}"`
- `python -m skills.simulink_scan --json "{\"action\":\"inspect\",\"model\":\"m\",\"target\":\"m/Gain\",\"param\":\"All\",\"summary\":true,\"session\":\"MATLAB_12345\"}"`

## Schema Action

- `python -m skills.simulink_scan schema`
- Returns machine-readable action and error-code contracts for agents.

## Scan Actions

- If multiple models are opened and `--model` is omitted, the tool returns `model_required` with candidate models.
- Shallow scan:
  - `python -m skills.simulink_scan scan --model "<model>"`
- Recursive scan:
  - `python -m skills.simulink_scan scan --model "<model>" --recursive`
- Subsystem scan:
  - `python -m skills.simulink_scan scan --model "<model>" --subsystem "<subsystem>" --recursive`
- Hierarchy output:
  - `python -m skills.simulink_scan scan --model "<model>" --hierarchy`
- Output clipping:
  - `python -m skills.simulink_scan scan --model "<model>" --max-blocks 200 --fields "name,type"`

## Inspect Actions

- Full parameter view:
  - `python -m skills.simulink_scan inspect --model "<model>" --target "<block>" --param "All"`
- Active-only parameters:
  - `python -m skills.simulink_scan inspect --model "<model>" --target "<block>" --param "All" --active-only`
- Summary mode:
  - `python -m skills.simulink_scan inspect --model "<model>" --target "<block>" --param "All" --summary`
- Strict active check:
  - `python -m skills.simulink_scan inspect --model "<model>" --target "<block>" --param "<name>" --strict-active`
- Resolve effective value:
  - `python -m skills.simulink_scan inspect --model "<model>" --target "<block>" --param "<name>" --resolve-effective`
- Output clipping:
  - `python -m skills.simulink_scan inspect --model "<model>" --target "<block>" --param "All" --max-params 50 --fields "target,values"`

## Highlight Action

- Highlight is supported as a read-only visual locator (implemented via `hilite_system`, no model mutation).
- Basic usage:
  - `python -m skills.simulink_scan highlight --target "<block>"`
- With explicit session:
  - `python -m skills.simulink_scan highlight --target "<block>" --session "MATLAB_12345"`
- If target path is invalid, command returns `block_not_found`.

## Recovery Matrix

| Error Code | Likely Cause | Next Command | Expected Success Signal |
|---|---|---|---|
| `engine_unavailable` | MATLAB Engine for Python is not available in active interpreter | install/configure MATLAB Engine for Python and rerun the same command | command runs without `engine_unavailable` |
| `session_required` | Multiple MATLAB shared sessions and no explicit target | `python -m skills.simulink_scan session list` then retry with `--session` | action returns payload without `error` |
| `session_not_found` | Session name is not an exact match | `python -m skills.simulink_scan session list` then copy exact name | action connects to requested session |
| `model_required` | Multiple opened models and no explicit model | `python -m skills.simulink_scan list_opened` then retry with `--model` | scan/inspect returns selected model |
| `inactive_parameter` | Requested parameter is inactive under current mask config | retry with `--resolve-effective` or `--strict-active` | response includes effective mapping or explicit inactive failure |
| `invalid_json` | Malformed JSON or wrong field type | validate payload using `schema`, then retry | request parses and executes |

## Troubleshooting

- If MATLAB Engine for Python is unavailable, install/configure it in the active interpreter first.
- If no shared MATLAB session is found, run `matlab.engine.shareEngine` in MATLAB.
- If `matlab.engine` import fails, install/configure MATLAB Engine for Python in the active environment.
