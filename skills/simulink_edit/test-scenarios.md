# simulink-edit Test Scenarios

## set_param Scenarios

- Dry-run preview: `--json '{"action":"set_param","target":"m/Gain1","param":"Gain","value":"2.0"}'` → dry_run=true, current_value, proposed_value, apply_payload, rollback
- Replay apply_payload: capture `apply_payload` from preview, pass it back as `--json` verbatim → dry_run=false, previous_value, new_value, verified, rollback
- Stale preview replay: capture `apply_payload`, change the target externally, then replay the saved payload → `precondition_failed`, `recommended_recovery="rerun_dry_run"`, no accidental mutation
- Execute verification failure: `--json '{"action":"set_param","target":"m/Gain1","param":"Gain","value":"2.0","dry_run":false}'` → `verification_failed`, `details.rollback`, write_state
- Block not found: `--json '{"action":"set_param","target":"m/Missing","param":"Gain","value":"2.0"}'` → `block_not_found`
- Param not found: `--json '{"action":"set_param","target":"m/Gain1","param":"NoSuch","value":"2.0"}'` → `param_not_found`
- Missing required field: `--json '{"action":"set_param","target":"m/Gain1"}'` → parser error (param, value required)
- Invalid JSON: `--json '{invalid}'` → `invalid_json`
- Unknown field: `--json '{"action":"set_param","target":"m/B","param":"P","value":"1","extra":"x"}'` → `unknown_parameter`
- Wrong type: `--json '{"action":"set_param","target":"m/B","param":"P","value":123}'` → `invalid_json` (value must be string)
- Literal percent value: `--json '{"action":"set_param","target":"m/Display","param":"Format","value":"%.3f"}'` → accepted preview/execute contract
- Multiline value: `--json '{"action":"set_param","target":"m/Display","param":"Comment","value":"Line 1\nLine 2"}'` → JSON mode preserves the newline payload exactly
- Rollback payload is executable: take `rollback` from any response, pass as `--json` → restores original
- Explicit session rollback: execute with `"session":"MATLAB_12345"` → returned rollback preserves the same session field

## Schema Scenarios

- Schema: `--json '{"action":"schema"}'` → actions includes set_param with fields
- Schema includes error codes: `param_not_found`, `precondition_failed`, `set_param_failed`, `verification_failed` in error_codes list

## model_new Scenarios

- Create new model: `--json '{"action":"model_new","name":"my_model"}'` → action=model_new, name, verified=true, rollback with available=false
- Create model that already exists: `--json '{"action":"model_new","name":"existing_model"}'` → `model_already_loaded`
- Missing name: `--json '{"action":"model_new"}'` → parser error (name required)

## model_open Scenarios

- Open model from file path: `--json '{"action":"model_open","path":"C:/models/my_model.slx"}'` → action=model_open, path
- Open already-open model: `--json '{"action":"model_open","path":"C:/models/my_model.slx"}'` → succeeds (idempotent)
- Open non-existent file: `--json '{"action":"model_open","path":"C:/missing.slx"}'` → `model_not_found`
- Missing path: `--json '{"action":"model_open"}'` → parser error (path required)

## model_save Scenarios

- Save loaded model: `--json '{"action":"model_save","model":"my_model"}'` → action=model_save, model
- Save non-loaded model: `--json '{"action":"model_save","model":"not_loaded"}'` → `model_not_found`
- Missing model: `--json '{"action":"model_save"}'` → parser error (model required)

## Cross-Skill Scenarios

- Full workflow: scan → find → inspect → set_param (dry_run) → replay apply_payload → inspect (verify)
- Rollback workflow: replay apply_payload → use rollback payload → inspect confirms original restored
