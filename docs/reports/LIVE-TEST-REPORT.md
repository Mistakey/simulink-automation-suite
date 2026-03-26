# Live Test Report

## Meta
| Field | Value |
|-------|-------|
| Plugin Version | 2.5.0 |
| Test Date | 2026-03-26 |
| Test Commit | 1671c0a |
| Test Mode | full |
| MATLAB Version | MATLAB_257680 (shared session) |
| Simulink Version | N/A (session list only) |

## Summary
| Total | Pass | Fail | Blocked | Skip |
|-------|------|------|---------|------|
| 37    | 36   | 1    | 0       | 0    |

Phase Coverage:
| Phase | Status |
|-------|--------|
| 0 Environment | ✅ PASS |
| 1 Meta | ✅ PASS |
| 2 Read-Only | ⚠️ PARTIAL (1 FAIL) |
| 3 Lifecycle & Write | ✅ PASS |
| 4 Error Handling | ✅ PASS |
| 5 Documentation | ✅ PASS |

## Results

### Phase 1: Meta
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | schema action | PASS | 1671c0a | Returns v2.5, 19 actions, 31 error codes |
| 2 | session list | PASS | 1671c0a | Returns MATLAB_257680 as active session |
| 3 | session current | PASS | 1671c0a | Returns active_session with active_source=single |
| 4 | list_opened | PASS | 1671c0a | Returns 13 opened models including Foc_BaseVer |

### Phase 2: Read-Only
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | scan (max_blocks=5, truncated) | PASS | 1671c0a | Returns 5/45 blocks, truncated=true |
| 2 | scan (fields projection) | PASS | 1671c0a | Returns all 45 blocks with only name+type fields |
| 3 | find (block_type=SubSystem, max_results=3) | FAIL | 1671c0a | FAIL-001: MATLAB variant warning leaks to stdout before JSON |
| 4 | inspect (specific param) | PASS | 1671c0a | Returns Value="Observer" for Foc_BaseVer/Constant |
| 5 | connections (downstream, depth=1) | PASS | 1671c0a | Returns downstream_blocks=[Foc_BaseVer/Multiport\nSwitch] |
| 6 | highlight | PASS | 1671c0a | Returns success status, highlighted=Foc_BaseVer/Constant |

### Phase 3: Lifecycle & Write
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | model_new (LiveTest25) | PASS | 1671c0a | verified=true; model appears in list_opened; MATLAB stdout noise noted as known issue |
| 2 | block_add (Gain block) | PASS | 1671c0a | verified=true; rollback payload present; MATLAB stdout noise |
| 3 | block_add (Constant block) | PASS | 1671c0a | verified=true; rollback payload present |
| 4 | line_add (Const1→Gain1) | PASS | 1671c0a | Returns line_handle, verified=true, rollback present |
| 5 | set_param dry_run=true | PASS | 1671c0a | Returns current_value=1, apply_payload, rollback |
| 6 | set_param dry_run=false | PASS | 1671c0a | write_state=verified, verified=true, new_value=5.0 |
| 7 | set_param read-back via inspect | PASS | 1671c0a | Gain confirmed=5.0 |
| 8 | model_save | PASS | 1671c0a | Returns success envelope |
| 9 | model_update | PASS | 1671c0a | Compiles; returns warnings array for empty sink model (expected) |
| 10 | simulate | PASS | 1671c0a | Returns warnings array; stdout warning note below |
| 11 | line_delete | PASS | 1671c0a | Returns rollback with line_add payload |
| 12 | block_delete (Gain1) | PASS | 1671c0a | verified=true; rollback notes source required for restore |
| 13 | block_delete (Const1) | PASS | 1671c0a | verified=true |
| 14 | model_close (dirty — expect error) | PASS | 1671c0a | Returns model_dirty with suggested_fix |
| 15 | model_close (force=true) | PASS | 1671c0a | Model closed successfully |

### Phase 4: Error Handling
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | scan (no model, multiple open) | PASS | 1671c0a | Returns model_required with model list |
| 2 | connections (missing required target) | PASS | 1671c0a | Returns invalid_json with field-level message |
| 3 | scan (wrong type: recursive="yes") | PASS | 1671c0a | Returns invalid_json "must be boolean" |
| 4 | unknown action | PASS | 1671c0a | Returns invalid_json "unsupported action" |
| 5 | model_not_found | PASS | 1671c0a | Returns model_not_found with opened model list |
| 6 | block_not_found (inspect) | PASS | 1671c0a | Returns block_not_found with suggested_fix |
| 7 | block_add invalid parent path | PASS | 1671c0a | Returns runtime_error with cause detail |

### Phase 5: Documentation
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | session_action field name matches schema | PASS | 1671c0a | SKILL.md uses session_action correctly |
| 2 | Write safety model (dry_run chain) | PASS | 1671c0a | apply_payload + expected_current_value + verified all confirmed |
| 3 | Error recovery routing table | PASS | 1671c0a | model_dirty, block_not_found, model_not_found, model_required all match docs |
| 4 | model_close/model_update in action table | PASS | 1671c0a | Both listed as Direct Handling; both work as documented |
| 5 | Output discipline rule (no raw stdout) | FAIL | 1671c0a | FAIL-001: docs say "warnings must not leak as raw text"; reality violates this |

## Failure Details

### FAIL-001: MATLAB stdout warnings leak before JSON output
- **Phase**: Phase 2 (Read-Only) and Phase 3 (Lifecycle & Write) and Phase 5 (Documentation)
- **Actions**: `find`, `model_new`, `block_add`, `block_delete`, `simulate`
- **Steps**:
  ```
  python -m simulink_cli --json '{"action":"find","model":"Foc_BaseVer","block_type":"SubSystem","max_results":3}'
  python -m simulink_cli --json '{"action":"model_new","name":"LiveTest25"}'
  python -m simulink_cli --json '{"action":"block_add","source":"simulink/Math Operations/Gain","destination":"LiveTest25/Gain1"}'
  ```
- **Expected**: Single JSON payload on stdout; no raw text before or after.
- **Actual**: MATLAB engine emits diagnostic/warning text on stdout before the JSON payload. Example for `find`:
  ```
  Warning: Using find_system without the 'Variants' argument skips inactive Variant Subsystem blocks...
  {"model": "Foc_BaseVer", ...}
  ```
  Example for `model_new`/`block_add`/`block_delete`:
  ```
  Invalid Simulink object name: 'LiveTest25/Gain1'.
  Caused by:
      Unable to find block 'Gain1'.
  {"action": "block_add", ...}
  ```
- **Root Cause**: The MATLAB Engine's stdout channel carries diagnostic messages emitted during `get_param` verification calls. These bypass the CLI's JSON formatter and land directly on process stdout.
- **Impact**: Agent JSON parsers that expect clean stdout will fail or require multiline-stripping heuristics. The `v2.2.1` fix (commit `290d8a4`) only suppressed warnings inside the JSON `results` array, not the raw engine stdout.
- **Commit**: 1671c0a

## Blocked Details

None.

## Suggestions

### Bug Fixes
- **FAIL-001 fix**: Redirect MATLAB Engine stdout during transport calls using `io.StringIO` capture or `matlab.engine` output capture parameters. All `eng.get_param()` and `eng.add_block()` verification calls should redirect `stdout` and `stderr` to capture objects, then discard or log to file — not forward to process stdout. This is the standard pattern for MATLAB Engine Python suppression.

### Optimization
- **block_add rollback availability**: When `block_delete` rollback notes `available: false` with a manual restore instruction, the message references a generic `<source>` placeholder. The plugin could persist the original source path in state to make rollback actionable. Low priority but improves agent recovery.
- **model_update warnings contain HTML**: The `model_update` and `simulate` `warnings` array contains MATLAB HTML anchor tags (`<a href="matlab:...">`) which are not meaningful in a CLI/agent context. Consider stripping HTML from warning strings before embedding in JSON.

### Missing Features
- **simulate with real output**: The `simulate` action ran successfully but returned only warnings. There is no way to retrieve simulation output data (workspace variables, logged signals) via CLI. For agents building closed-loop control workflows, post-simulation data extraction would be a natural next step.
- **block_add rollback source persistence**: As noted above — the rollback payload for `block_delete` cannot automatically restore the block without knowing the original library source.

## Run History
| Date | Mode | Commit | Result | Notes |
|------|------|--------|--------|-------|
| 2026-03-24 | full | 7244e65 | ✅ 20/20 PASS | Initial full test, v2.2.0 |
| 2026-03-26 | full | 1671c0a | ⚠️ 36/37 PASS | Full test v2.5.0; FAIL-001 stdout contamination across multiple actions |

## Schema Snapshot
```json
{"version": "2.5", "actions": {"schema": {"description": "Return machine-readable command contract and error-code catalog.", "fields": {}}, "scan": {"description": "Read model or subsystem topology with optional hierarchy view.", "fields": {"model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."}, "subsystem": {"type": "string", "required": false, "default": null, "description": "Optional subsystem path under model."}, "recursive": {"type": "boolean", "required": false, "default": false, "description": "Recursively scan all nested blocks under scan root."}, "hierarchy": {"type": "boolean", "required": false, "default": false, "description": "Include hierarchy tree in output (implies recursive)."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}, "max_blocks": {"type": "integer", "required": false, "default": null, "description": "Limit number of block entries returned."}, "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected block fields to include."}}}, "connections": {"description": "Read upstream/downstream block relationships from a target block.", "fields": {"model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."}, "target": {"type": "string", "required": true, "default": null, "description": "Block path to analyze."}, "direction": {"type": "string", "required": false, "default": "both", "enum": ["upstream", "downstream", "both"], "description": "Traversal direction from target block."}, "depth": {"type": "integer", "required": false, "default": 1, "description": "Traversal depth in hops."}, "detail": {"type": "string", "required": false, "default": "summary", "enum": ["summary", "ports", "lines"], "description": "Output detail level."}, "include_handles": {"type": "boolean", "required": false, "default": false, "description": "Include line handles in lines detail output."}, "max_edges": {"type": "integer", "required": false, "default": null, "description": "Limit number of connection edges returned."}, "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected top-level response fields to include."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}}}, "highlight": {"description": "Highlight a target block in Simulink UI.", "fields": {"target": {"type": "string", "required": true, "default": null, "description": "Block path to highlight."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}}}, "inspect": {"description": "Read block parameters and effective values.", "fields": {"model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."}, "target": {"type": "string", "required": true, "default": null, "description": "Block path to inspect."}, "param": {"type": "string", "required": false, "default": "All", "description": "Parameter name to read, or All for dialog parameters."}, "active_only": {"type": "boolean", "required": false, "default": false, "description": "Return only active parameters when param=All."}, "strict_active": {"type": "boolean", "required": false, "default": false, "description": "Fail when requested parameter is inactive."}, "resolve_effective": {"type": "boolean", "required": false, "default": false, "description": "Resolve known effective value for inactive parameter."}, "summary": {"type": "boolean", "required": false, "default": false, "description": "Include compact summary lists when param=All."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}, "max_params": {"type": "integer", "required": false, "default": null, "description": "Limit number of parameters returned when param=All."}, "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected top-level response fields to include."}}}, "find": {"description": "Search for blocks by name pattern and/or block type.", "fields": {"model": {"type": "string", "required": false, "default": null, "description": "Target model (same resolution as scan)."}, "subsystem": {"type": "string", "required": false, "default": null, "description": "Narrow search scope to a subsystem."}, "name": {"type": "string", "required": false, "default": null, "description": "Name substring match (case-insensitive)."}, "block_type": {"type": "string", "required": false, "default": null, "description": "BlockType exact match (e.g., SubSystem, Gain)."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}, "max_results": {"type": "integer", "required": false, "default": 200, "description": "Limit number of results returned."}, "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected result fields to include."}}}, "list_opened": {"description": "List currently opened Simulink models.", "fields": {"session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}}}, "set_param": {"description": "Set a block parameter with dry-run preview and rollback support.", "fields": {"target": {"type": "string", "required": true, "default": null, "description": "Full block path to modify."}, "param": {"type": "string", "required": true, "default": null, "description": "Parameter name."}, "value": {"type": "string", "required": true, "default": null, "description": "New parameter value (always string — MATLAB handles conversion)."}, "expected_current_value": {"type": "string", "required": false, "default": null, "description": "Optional guarded-execute precondition from a dry-run preview."}, "dry_run": {"type": "boolean", "required": false, "default": true, "description": "Preview mode — show diff without writing. Defaults to true."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "session": {"description": "Manage active MATLAB shared session selection.", "fields": {"session_action": {"type": "string", "required": true, "default": null, "enum": ["list", "use", "current", "clear"], "description": "Session management operation.", "positional": true}, "name": {"type": "string", "required": false, "default": null, "description": "Session name, required when session_action=use.", "positional_optional": true}}}, "model_new": {"description": "Create a new Simulink model.", "fields": {"name": {"type": "string", "required": true, "default": null, "description": "Name for the new model."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "model_open": {"description": "Open a Simulink model from file path or MATLAB path.", "fields": {"path": {"type": "string", "required": true, "default": null, "description": "File path or model name to open."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "model_save": {"description": "Save a loaded Simulink model to disk.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Name of the loaded model to save."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "model_close": {"description": "Close a loaded Simulink model.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Model name to close."}, "force": {"type": "boolean", "required": false, "default": false, "description": "Close even if model has unsaved changes."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "model_update": {"description": "Compile/update a loaded Simulink model diagram.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Model name to update/compile."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "block_add": {"description": "Add a block to a loaded Simulink model.", "fields": {"source": {"type": "string", "required": true, "default": null, "description": "Library source path (e.g. 'simulink/Math Operations/Gain')."}, "destination": {"type": "string", "required": true, "default": null, "description": "Full block path in model (e.g. 'my_model/Gain1')."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "block_delete": {"description": "Delete a block from a loaded Simulink model.", "fields": {"destination": {"type": "string", "required": true, "default": null, "description": "Full block path in model (e.g. 'my_model/Gain1')."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "line_add": {"description": "Connect two block ports with a signal line.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Target model or subsystem path."}, "src_block": {"type": "string", "required": true, "default": null, "description": "Source block name (local to model, must not contain '/')."}, "src_port": {"type": "integer", "required": true, "default": null, "description": "Source output port number."}, "dst_block": {"type": "string", "required": true, "default": null, "description": "Destination block name (local to model, must not contain '/')."}, "dst_port": {"type": "integer", "required": true, "default": null, "description": "Destination input port number."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "line_delete": {"description": "Delete a signal line between two block ports.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Target model or subsystem path."}, "src_block": {"type": "string", "required": true, "default": null, "description": "Source block name (local to model, must not contain '/')."}, "src_port": {"type": "integer", "required": true, "default": null, "description": "Source output port number."}, "dst_block": {"type": "string", "required": true, "default": null, "description": "Destination block name (local to model, must not contain '/')."}, "dst_port": {"type": "integer", "required": true, "default": null, "description": "Destination input port number."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "simulate": {"description": "Run simulation on a loaded Simulink model.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Model name to simulate."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}}, "error_codes": ["block_already_exists", "block_not_found", "engine_unavailable", "inactive_parameter", "invalid_input", "invalid_json", "invalid_subsystem_type", "json_conflict", "line_already_exists", "line_not_found", "model_already_loaded", "model_dirty", "model_not_found", "model_required", "model_save_failed", "no_session", "param_not_found", "port_not_found", "precondition_failed", "runtime_error", "session_not_found", "session_required", "set_param_failed", "simulation_failed", "source_not_found", "state_clear_failed", "state_write_failed", "subsystem_not_found", "unknown_parameter", "update_failed", "verification_failed"]}
```
