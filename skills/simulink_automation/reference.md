# simulink-automation Reference

This file contains response shape examples and failure semantics that cannot be derived from `schema` output.
For action fields, types, and error codes, call `python -m simulink_cli schema`.

## set_param Response Shapes

### Dry-Run (Preview)

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

Replay `apply_payload` from preview verbatim in JSON mode.

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

### Stale Preview Rejection

If current value changed after preview, `apply_payload` replay returns `precondition_failed` without writing:

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

### Rollback

Use the `rollback` payload from any response to restore the prior value. If the original write used an explicit `session`, the rollback payload preserves the same `session` field.

## set_param Multi-Param Response Shapes

### Dry-Run (Multi-Param Preview)

```json
{
  "action": "set_param",
  "dry_run": true,
  "write_state": "not_attempted",
  "target": "m/PWM_Carrier",
  "changes": [
    {"param": "rep_seq_t", "current_value": "[0 1]", "proposed_value": "[0 5e-5 1e-4]"},
    {"param": "rep_seq_y", "current_value": "[0 1]", "proposed_value": "[-1 1 -1]"}
  ],
  "apply_payload": {
    "action": "set_param",
    "target": "m/PWM_Carrier",
    "params": {"rep_seq_t": "[0 5e-5 1e-4]", "rep_seq_y": "[-1 1 -1]"},
    "dry_run": false,
    "expected_current_values": {"rep_seq_t": "[0 1]", "rep_seq_y": "[0 1]"}
  },
  "rollback": {
    "action": "set_param",
    "target": "m/PWM_Carrier",
    "params": {"rep_seq_t": "[0 1]", "rep_seq_y": "[0 1]"},
    "dry_run": false
  }
}
```

### Execute (Multi-Param)

Replay `apply_payload` from multi-param preview verbatim in JSON mode.

```json
{
  "action": "set_param",
  "dry_run": false,
  "write_state": "verified",
  "target": "m/PWM_Carrier",
  "changes": [
    {"param": "rep_seq_t", "previous_value": "[0 1]", "new_value": "[0 5e-5 1e-4]"},
    {"param": "rep_seq_y", "previous_value": "[0 1]", "new_value": "[-1 1 -1]"}
  ],
  "verified": true,
  "rollback": {
    "action": "set_param",
    "target": "m/PWM_Carrier",
    "params": {"rep_seq_t": "[0 1]", "rep_seq_y": "[0 1]"},
    "dry_run": false
  }
}
```

## block_add Response Shapes

### Success

```json
{
  "action": "block_add",
  "source": "simulink/Math Operations/Gain",
  "destination": "my_model/Gain1",
  "verified": true,
  "rollback": {
    "action": "block_delete",
    "destination": "my_model/Gain1"
  }
}
```

Rollback uses `block_delete`. If the original request used an explicit `session`, the rollback payload preserves the same `session` field.

## line_add Response Shapes

### Success

```json
{
  "action": "line_add",
  "model": "my_model",
  "line_handle": 145.0001,
  "verified": true,
  "rollback": {
    "action": "line_delete",
    "model": "my_model",
    "src_block": "Sine",
    "src_port": 1,
    "dst_block": "Gain",
    "dst_port": 1,
    "available": true
  }
}
```

### Success (Physical Port)

```json
{
  "action": "line_add",
  "model": "my_model",
  "line_handle": 145.0001,
  "verified": true,
  "rollback": {
    "action": "line_delete",
    "model": "my_model",
    "src_block": "DC_Source",
    "src_port": "RConn1",
    "dst_block": "Ground1",
    "dst_port": "LConn1",
    "available": true
  }
}
```

Rollback uses `line_delete`. If the original request used an explicit `session`, the rollback payload preserves the same `session` field.

## line_delete Response Shapes

### Success

```json
{
  "action": "line_delete",
  "model": "my_model",
  "src_block": "Sine",
  "src_port": 1,
  "dst_block": "Gain",
  "dst_port": 1,
  "rollback": {
    "action": "line_add",
    "model": "my_model",
    "src_block": "Sine",
    "src_port": 1,
    "dst_block": "Gain",
    "dst_port": 1,
    "available": true
  }
}
```

### Line Not Found

If the specified signal line does not exist between the given ports:

```json
{
  "error": "line_not_found",
  "message": "No line found from 'Sine/1' to 'Gain/1' in model 'my_model'.",
  "details": {"src": "Sine/1", "dst": "Gain/1", "model": "mymodel"},
  "suggested_fix": "Use {\"action\":\"connections\"} to verify existing connections before deleting."
}
```

## block_delete Response Shapes

### Success

```json
{
  "action": "block_delete",
  "destination": "my_model/Gain1",
  "verified": true,
  "rollback": {
    "available": false,
    "note": "Block deletion also removes connected lines. Use block_add to re-create with library defaults."
  }
}
```

### Block Not Found

```json
{
  "error": "block_not_found",
  "message": "Block 'my_model/Gain1' not found.",
  "details": {"destination": "my_model/Gain1"},
  "suggested_fix": "Use {\"action\":\"find\"} or {\"action\":\"scan\"} to locate valid block paths."
}
```

Possible errors: `model_not_found`, `block_not_found`, `verification_failed`, `runtime_error`.

## simulate Response Shapes

### Success

```json
{
  "action": "simulate",
  "model": "my_model",
  "warnings": []
}
```

### Simulation Failed

If MATLAB raises an error during simulation:

```json
{
  "error": "simulation_failed",
  "message": "Simulation of 'my_model' failed: <matlab_error_message>",
  "details": {"model": "demo", "cause": "<matlab_error_message>"},
  "suggested_fix": "Run {\"action\":\"model_update\"} to check for model errors, fix them, then retry."
}
```

## model_close Response Shapes

### Success

```json
{
  "action": "model_close",
  "model": "my_model",
  "force": false
}
```

### Dirty Model Rejection

If the model has unsaved changes and `force` is not `true`:

```json
{
  "error": "model_dirty",
  "message": "Model 'my_model' has unsaved changes.",
  "details": {"model": "my_model"},
  "suggested_fix": "Save first with {\"action\":\"model_save\",\"model\":\"my_model\"} or close with {\"action\":\"model_close\",\"model\":\"my_model\",\"force\":true}"
}
```

## model_update Response Shapes

### Success

```json
{
  "action": "model_update",
  "model": "my_model",
  "diagnostics": [],
  "warnings": []
}
```

The `warnings` field is a list of warning messages from the MATLAB compilation process. The `diagnostics` field contains parsed lines from MATLAB command window output during compilation. Both are empty lists on a clean update.

### Diagnostics

The `diagnostics` field contains parsed MATLAB compilation output lines. Each entry is a trimmed non-empty line from the MATLAB command window during model update.

```json
{
  "action": "model_update",
  "model": "my_model",
  "diagnostics": [
    "Warning: Block 'my_model/Gain1' has unconnected input port 2."
  ],
  "warnings": ["Block 'my_model/Gain1' has unconnected input port 2."]
}
```

## Failure Semantics

- `precondition_failed` — preview is stale; write was **not attempted**.
- `verification_failed` — write ran, but read-back did not confirm the requested value.
- `set_param_failed` — MATLAB rejected the write call.

All failure payloads include:
- `write_state`: `not_attempted` | `attempted` | `verified` | `verification_failed`
- `safe_to_retry`: boolean
- `recommended_recovery`: machine-readable recovery hint
- `details.rollback`: rollback payload for restoring prior value

## Value Type Notes

The `value` field is always a string. MATLAB's `set_param` handles type conversion:
- Numeric: `"2.0"`, `"100"`
- Boolean-like: `"on"`, `"off"`
- Enum: `"Continuous"`, `"Discrete"`
- Format strings: `"%.3f"`, `"%0.1f rpm"`
- Expression: `"1/(2*pi*100)"`
