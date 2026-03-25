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
    "destination": "my_model/Gain1",
    "available": false,
    "note": "block_delete not yet implemented (Phase 3)"
  }
}
```

Rollback is deferred — `block_delete` is not yet implemented. The `note` field provides a manual MATLAB command for undo. If the original request used an explicit `session`, the rollback payload preserves the same `session` field.

## line_add Response Shapes

### Success

```json
{
  "action": "line_add",
  "model": "my_model",
  "line_handle": 145.0003,
  "verified": true,
  "rollback": {
    "action": "line_delete",
    "model": "my_model",
    "line_handle": 145.0003,
    "available": false,
    "note": "line_delete not yet implemented (v2.5.0)"
  }
}
```

Rollback is deferred — `line_delete` is not yet implemented. If the original request used an explicit `session`, the rollback payload preserves the same `session` field.

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
  "warnings": []
}
```

The `warnings` field is a list of warning messages from the MATLAB compilation process. Empty list means no warnings.

## Failure Semantics

- `precondition_failed` — preview is stale; write was **not attempted**.
- `verification_failed` — write ran, but read-back did not confirm the requested value.
- `set_param_failed` — MATLAB rejected the write call.

All failure payloads include:
- `write_state`: `not_attempted` | `attempted` | `verified` | `failed_verification`
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
