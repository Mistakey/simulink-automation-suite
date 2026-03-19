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

```bash
python -m simulink_cli set_param --target "my_model/Gain1" --param "Gain" --value "2.0" --no-dry-run
```

```bash
python -m simulink_cli --json '{"action":"set_param","target":"my_model/Gain1","param":"Gain","value":"2.0","dry_run":false}'
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

## Recovery Matrix

| Error Code | Scenario | Suggested Fix | Success Looks Like |
|---|---|---|---|
| `block_not_found` | Target block path invalid | Run `simulink-scan find` to locate correct path | set_param succeeds |
| `param_not_found` | Parameter name not on block | Run `simulink-scan inspect` to list parameters | set_param succeeds |
| `set_param_failed` | MATLAB rejected the value | Check value format; read parameter constraints | set_param succeeds |
| `engine_unavailable` | MATLAB Engine not installed | Install MATLAB Engine for Python | set_param succeeds |
| `no_session` | No shared session | Run `matlab.engine.shareEngine` in MATLAB | set_param succeeds |
| `session_required` | Multiple sessions, no active/explicit target | Run `session list`, then either `session use <name>` or pass explicit `--session` | set_param succeeds |
| `session_not_found` | Named session not found | Check session name, rerun `session list` | set_param succeeds |
| `invalid_input` | Field validation failed | Fix input (control chars, whitespace, length) | set_param succeeds |
| `invalid_json` | Malformed JSON payload | Fix JSON syntax | set_param succeeds |
| `unknown_parameter` | Unrecognized field in JSON | Check `schema` for valid fields | set_param succeeds |
| `json_conflict` | Mixed --json and flags | Use one mode exclusively | set_param succeeds |

## Value Type Notes

The `value` field is always a string. MATLAB's `set_param` accepts string values and handles type conversion internally:
- Numeric: `"2.0"`, `"100"`
- Boolean-like: `"on"`, `"off"`
- Enum: `"Continuous"`, `"Discrete"`
- Format strings with literal percent signs: `"%.3f"`, `"%0.1f rpm"`
- Expression: `"1/(2*pi*100)"`
