# simulink-edit Test Scenarios

## set_param Scenarios

- Dry-run preview: `--json '{"action":"set_param","target":"m/Gain1","param":"Gain","value":"2.0"}'` → dry_run=true, current_value, proposed_value, rollback
- Execute: `--json '{"action":"set_param","target":"m/Gain1","param":"Gain","value":"2.0","dry_run":false}'` → dry_run=false, previous_value, new_value, verified, rollback
- Block not found: `--json '{"action":"set_param","target":"m/Missing","param":"Gain","value":"2.0"}'` → `block_not_found`
- Param not found: `--json '{"action":"set_param","target":"m/Gain1","param":"NoSuch","value":"2.0"}'` → `param_not_found`
- Missing required field: `--json '{"action":"set_param","target":"m/Gain1"}'` → parser error (param, value required)
- Invalid JSON: `--json '{invalid}'` → `invalid_json`
- Unknown field: `--json '{"action":"set_param","target":"m/B","param":"P","value":"1","extra":"x"}'` → `unknown_parameter`
- Wrong type: `--json '{"action":"set_param","target":"m/B","param":"P","value":123}'` → `invalid_json` (value must be string)
- Literal percent value: `--json '{"action":"set_param","target":"m/Display","param":"Format","value":"%.3f"}'` → accepted preview/execute contract
- Rollback payload is executable: take `rollback` from any response, pass as `--json` → restores original
- Explicit session rollback: execute with `"session":"MATLAB_12345"` → returned rollback preserves the same session field

## Schema Scenarios

- Schema: `--json '{"action":"schema"}'` → actions includes set_param with fields
- Schema includes error codes: `param_not_found`, `set_param_failed` in error_codes list

## Cross-Skill Scenarios

- Full workflow: scan → find → inspect → set_param (dry) → set_param (execute) → inspect (verify)
- Rollback workflow: set_param (execute) → use rollback payload → verify original restored
