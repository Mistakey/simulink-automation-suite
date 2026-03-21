# simulink-edit Reference

## set_param Action

### Dry-Run (Preview)

```bash
python -m simulink_cli set_param --target "my_model/Gain1" --param "Gain" --value "2.0"
```

```bash
python -m simulink_cli --json '{"action":"set_param","target":"my_model/Gain1","param":"Gain","value":"2.0"}'
```

Output:
```json
{
  "action": "set_param",
  "dry_run": true,
  "target": "my_model/Gain1",
  "param": "Gain",
  "current_value": "1.5",
  "proposed_value": "2.0",
  "apply_payload": {
    "action": "set_param",
    "target": "my_model/Gain1",
    "param": "Gain",
    "value": "2.0",
    "dry_run": false,
    "expected_current_value": "1.5"
  },
  "rollback": {
    "action": "set_param",
    "target": "my_model/Gain1",
    "param": "Gain",
    "value": "1.5",
    "dry_run": false
  }
}
```

### Execute

Replay the `apply_payload` from preview instead of reconstructing the execute request:

```bash
python -m simulink_cli --json '{"action":"set_param","target":"my_model/Gain1","param":"Gain","value":"2.0","dry_run":false,"expected_current_value":"1.5"}'
```

```bash
python -m simulink_cli --json '<paste apply_payload from preview response verbatim>'
```

Output:
```json
{
  "action": "set_param",
  "dry_run": false,
  "target": "my_model/Gain1",
  "param": "Gain",
  "previous_value": "1.5",
  "new_value": "2.0",
  "verified": true,
  "rollback": {
    "action": "set_param",
    "target": "my_model/Gain1",
    "param": "Gain",
    "value": "1.5",
    "dry_run": false
  }
}
```

### Rollback

Use the `rollback` payload from any response to undo the change:

```bash
python -m simulink_cli --json '{"action":"set_param","target":"my_model/Gain1","param":"Gain","value":"1.5","dry_run":false}'
```

If the original write used an explicit `session`, the rollback payload preserves the same `session` field so it can be replayed directly.

### Stale Preview Rejection

If the current value changes after preview, replaying the saved `apply_payload` returns `precondition_failed` without mutating the model:

```json
{
  "error": "precondition_failed",
  "details": {
    "expected_current_value": "1.5",
    "observed_current_value": "9.0",
    "write_state": "not_attempted",
    "safe_to_retry": true,
    "recommended_recovery": "rerun_dry_run"
  }
}
```

## Failure Semantics

Execute-mode failures must preserve enough information for recovery:

- `precondition_failed` means the preview is stale; the write was not attempted.
- `verification_failed` means the write ran, but read-back did not confirm the requested value.
- The failure payload includes `write_state` so the caller can tell whether the write was not attempted, attempted, verified, or failed verification.
- The failure payload includes `safe_to_retry` and `recommended_recovery` for machine recovery routing.
- The failure payload includes `details.rollback` so the caller can restore the prior value without reconstructing it manually.
- `set_param_failed` remains the top-level code for write-call failures.

## Recovery Matrix

| Error Code | Scenario | Suggested Fix | Success Looks Like |
|---|---|---|---|
| `block_not_found` | Target block path invalid | Run `simulink-scan find` to locate correct path | set_param succeeds |
| `param_not_found` | Parameter name not on block | Run `simulink-scan inspect` to list parameters | set_param succeeds |
| `precondition_failed` | Preview is stale | Rerun dry-run and replay the new `apply_payload` | set_param succeeds |
| `set_param_failed` | MATLAB rejected the value or write-call failed | Check value format, inspect constraints, then retry cautiously | set_param succeeds |
| `verification_failed` | Read-back did not confirm the requested write | Inspect the target again or use `details.rollback` | set_param succeeds |
| `engine_unavailable` | MATLAB Engine not installed | Install MATLAB Engine for Python | set_param succeeds |
| `no_session` | No shared session | Run `matlab.engine.shareEngine` in MATLAB | set_param succeeds |
| `session_required` | Multiple sessions, no active/explicit target | Run `session list`, then either `session use <name>` or pass explicit `--session` | set_param succeeds |
| `session_not_found` | Named session not found | Check session name, rerun `session list` | set_param succeeds |
| `invalid_input` | Field validation failed | Fix input (control chars, whitespace, length) | set_param succeeds |
| `invalid_json` | Malformed JSON payload | Fix JSON syntax | set_param succeeds |
| `unknown_parameter` | Unrecognized field in JSON | Check `schema` for valid fields | set_param succeeds |
| `json_conflict` | Mixed --json and flags | Use one mode exclusively | set_param succeeds |
| `model_already_loaded` | Model name already in memory | Use a different name or close existing model | model_new succeeds |
| `model_not_found` | Model not loaded or file not found | Open or create the model first | model_open/model_save succeeds |
| `model_save_failed` | Save operation failed | Check file permissions and disk space | model_save succeeds |

## Model Lifecycle Actions

### model_new — Create a New Model

```bash
python -m simulink_cli --json '{"action":"model_new","name":"my_model"}'
```

Output:
```json
{
  "action": "model_new",
  "name": "my_model",
  "verified": true,
  "rollback": {
    "action": "model_close",
    "model": "my_model",
    "available": false,
    "note": "model_close not yet implemented; use MATLAB close_system('my_model', 0) manually to undo"
  }
}
```

Error when model already loaded:
```json
{
  "error": "model_already_loaded",
  "message": "Model 'my_model' is already loaded.",
  "details": {"name": "my_model"},
  "suggested_fix": "Use a different name or close the existing model first."
}
```

### model_open — Open an Existing Model

```bash
python -m simulink_cli --json '{"action":"model_open","path":"C:/models/my_model.slx"}'
```

Output:
```json
{
  "action": "model_open",
  "path": "C:/models/my_model.slx"
}
```

`model_open` is idempotent — opening an already-open model brings it to the foreground without error.

### model_save — Save a Loaded Model

```bash
python -m simulink_cli --json '{"action":"model_save","model":"my_model"}'
```

Output:
```json
{
  "action": "model_save",
  "model": "my_model"
}
```

## Value Type Notes

The `value` field is always a string. MATLAB's `set_param` accepts string values and handles type conversion internally:
- Numeric: `"2.0"`, `"100"`
- Boolean-like: `"on"`, `"off"`
- Enum: `"Continuous"`, `"Discrete"`
- Format strings with literal percent signs: `"%.3f"`, `"%0.1f rpm"`
- Expression: `"1/(2*pi*100)"`
