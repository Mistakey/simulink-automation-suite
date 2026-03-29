# Live Test Report

## Meta
| Field | Value |
|-------|-------|
| Plugin Version | 2.7.1 |
| Test Date | 2026-03-29 |
| Test Commit | 00ef2f9 |
| Test Mode | incremental |
| MATLAB Version | MATLAB_257680 (shared session) |
| Simulink Version | N/A (session list only) |

## Summary
| Total | Pass | Fail | Blocked | Skip |
|-------|------|------|---------|------|
| 43    | 43   | 0    | 0       | 0    |

Phase Coverage:
| Phase | Status |
|-------|--------|
| 0 Environment | ✅ PASS |
| 1 Meta | ✅ PASS |
| 2 Read-Only | ✅ PASS |
| 3 Lifecycle & Write | ✅ PASS |
| 4 Error Handling | ✅ PASS |
| 5 Documentation | ✅ PASS |

## Results

### Phase 1: Meta
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | schema action | PASS | 31245ca | Returns v2.7, 20 actions, 33 error codes |
| 2 | session list | PASS | 31245ca | Returns MATLAB_257680 as active session |
| 3 | session current | PASS | 31245ca | Returns active_session with active_source=single |
| 4 | list_opened | PASS | 31245ca | Returns 16 opened models including Foc_BaseVer |

### Phase 2: Read-Only
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | scan (max_blocks=5, truncated) | PASS | 31245ca | Returns 5/43 blocks, truncated=true |
| 2 | scan (fields projection) | PASS | 31245ca | Returns all 43 blocks with only name+type fields |
| 3 | find (FAIL-001 regression — stdout noise) | PASS | 31245ca | Fixed in 9498d82: clean JSON, no stdout noise before output |
| 4 | inspect (specific param) | PASS | 31245ca | Returns Value="Observer" for Foc_BaseVer/Constant |
| 5 | connections (downstream, depth=1) | PASS | 31245ca | Returns downstream_blocks=[Foc_BaseVer/Multiport\nSwitch] |
| 6 | highlight | PASS | 31245ca | Returns success status, highlighted=Foc_BaseVer/Constant |

### Phase 3: Lifecycle & Write
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | model_new (LiveTest29) | PASS | 31245ca | verified=true; appears in list_opened |
| 2 | block_add (basic, no position) | PASS | 31245ca | verified=true; rollback payload present |
| 3 | block_add (position=[50,50,130,80]) | PASS | 00ef2f9 | Fixed in 3f63378: position field present in response; verified=true |
| 4 | block_add (auto_layout=true) | PASS | 31245ca | verified=true; auto_layout accepted and applied |
| 5 | line_add (signal, integer ports) | PASS | 31245ca | Returns line_handle, verified=true, rollback present |
| 6 | set_param single dry_run=true | PASS | 31245ca | Returns current_value, proposed_value, apply_payload, rollback |
| 7 | set_param multi-param dry_run=true (F-006) | PASS | 31245ca | Returns changes array with expected_current_values in apply_payload |
| 8 | set_param single dry_run=false | PASS | 31245ca | write_state=verified, new_value=10 |
| 9 | set_param multi-param dry_run=false (F-006) | PASS | 31245ca | write_state=verified; changes with previous_value/new_value per param |
| 10 | set_param read-back via inspect | PASS | 31245ca | Gain=10 confirmed via inspect |
| 11 | model_update | PASS | 00ef2f9 | Fixed in 3f63378: returns diagnostics=[] + warnings array |
| 12 | simulate (stop_time=1.0, max_step=0.1 overrides) | PASS | 31245ca | Returns overrides field with StopTime/MaxStep; expected warnings for empty sink |
| 13 | model_save | PASS | 31245ca | Returns success envelope |
| 14 | model_close (dirty — expect error) | PASS | 31245ca | Returns model_dirty with suggested_fix |
| 15 | model_close (force=true) | PASS | 31245ca | Model closed successfully |
| 16 | matlab_eval (F-001) | PASS | 00ef2f9 | Fixed in 3f63378: output="    42\n\n", truncated=false, warnings=[] |
| 17 | line_add physical port RConn1/LConn1 (F-003) | PASS | 31245ca | Returns line_handle, verified=true; rollback payload preserves string port names |
| 18 | line_delete physical port RConn1/LConn1 (F-003) | PASS | 31245ca | Returns rollback with line_add and string port names |

### Phase 4: Error Handling
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | scan (no model, multiple open) | PASS | 31245ca | Returns model_required with opened model list |
| 2 | connections (missing required target) | PASS | 31245ca | Returns invalid_json "field 'target' is required" |
| 3 | scan (wrong type: recursive="yes") | PASS | 31245ca | Returns invalid_json "must be boolean" |
| 4 | unknown action | PASS | 31245ca | Returns invalid_json "unsupported action" |
| 5 | model_not_found | PASS | 31245ca | Returns model_not_found with opened model list |
| 6 | block_not_found (inspect) | PASS | 31245ca | Returns block_not_found with suggested_fix |
| 7 | precondition_failed (single param) | PASS | 31245ca | Returns expected/observed, safe_to_retry, recommended_recovery=rerun_dry_run |
| 8 | precondition_failed (multi-param expected_current_values, F-006) | PASS | 31245ca | Returns precondition_failed, write_state=not_attempted |
| 9 | block_add invalid path → runtime_error | PASS | 31245ca | Returns runtime_error with cause detail |

### Phase 5: Documentation
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | FAIL-001 stdout discipline (fix verified) | PASS | 31245ca | find, model_new, block_add all return clean JSON; no stdout pollution |
| 2 | set_param single write safety chain (dry_run→apply→verify) | PASS | 31245ca | SKILL.md and reference.md match actual behavior |
| 3 | set_param multi-param write safety chain (F-006) | PASS | 31245ca | reference.md multi-param shapes match actual response exactly |
| 4 | Error recovery routing table | PASS | 31245ca | eval_failed/eval_timeout present; model_dirty/precondition_failed/block_not_found all match |
| 5 | SKILL.md Known Limitations stale content | PASS | 00ef2f9 | Fixed in 3f63378: 3 stale rows removed; single-param note updated to mention both modes |
| 6 | reference.md line_add signal success response shape | PASS | 00ef2f9 | Fixed in 3f63378: line_handle at top level; src_block/src_port in rollback only |

## Failure Details

### [RESOLVED in 9498d82] FAIL-001: MATLAB stdout warnings leak before JSON output
- **Phase**: Phase 2 (Read-Only), Phase 3 (Lifecycle & Write), Phase 5 (Documentation)
- **Actions**: `find`, `model_new`, `block_add`, `block_delete`, `simulate`
- **Expected**: Single JSON payload on stdout; no raw text before or after.
- **Actual**: MATLAB engine emitted diagnostic/warning text on stdout before the JSON payload.
- **Fix**: Commit `9498d82` — MATLAB Engine stdout/stderr suppressed in transport layer. Verified PASS in Phase 2 (find) and Phase 3 (model_new, block_add).

### [RESOLVED in 3f63378] FAIL-002: block_add position parameter fails
- **Phase**: Phase 3 (Lifecycle & Write)
- **Action**: `block_add`
- **Steps**:
  ```
  python -m simulink_cli --json '{"action":"block_add","source":"simulink/Sources/Constant","destination":"LiveTest29/Const1","position":[50,50,130,80]}'
  python -m simulink_cli --json '{"action":"block_add","source":"simulink/Sources/Constant","destination":"LiveTest29/Const1","position":[100,100,230,160]}'
  ```
- **Expected**: Block added at specified pixel position.
- **Actual**: `runtime_error` — "Invalid setting in Constant block 'Const1' for parameter 'Position'". Error persists across different position values.
- **Root Cause**: The `position` Python list is likely passed directly to `set_param(dst, 'Position', position)` without conversion to a MATLAB double array (`matlab.double([l,t,r,b])`). MATLAB's `set_param` requires a numeric array, not a Python list.
- **Commit**: 31245ca

### [RESOLVED in 3f63378] FAIL-003: model_update and matlab_eval fail with evalc_async undefined
- **Phase**: Phase 3 (Lifecycle & Write)
- **Actions**: `model_update`, `matlab_eval`
- **Steps**:
  ```
  python -m simulink_cli --json '{"action":"model_update","model":"LiveTest29"}'
  python -m simulink_cli --json '{"action":"matlab_eval","code":"x = 42; disp(x)"}'
  ```
- **Expected**: Successful compilation / code execution with output captured.
- **Actual**: Both return `runtime_error`/`eval_failed` — "Undefined function 'evalc_async' for input arguments of type 'char'". The MATLAB command window also prints "Unrecognized function or variable 'evalc_async'" before the JSON envelope.
- **Root Cause**: Implementation uses an `evalc_async` helper function that does not exist in this MATLAB installation. The function is either a custom helper that was not deployed, or targets a MATLAB version that includes it as a built-in. `evalc` (synchronous) is the standard MATLAB function for capturing command output.
- **Impact**: `model_update` (I-003 diagnostics) and `matlab_eval` (F-001) are fully non-functional on this device.
- **Commit**: 31245ca

### [RESOLVED in 3f63378] FAIL-004: SKILL.md contains stale Known Limitations after v2.5.1–v2.7.0 features
- **Phase**: Phase 5 (Documentation)
- **File**: `skills/simulink_automation/SKILL.md`
- **Issues**:
  1. **Line 37**: "One parameter per `set_param` invocation." — Stale after F-006 (multi-param `params` field added in v2.7.0).
  2. **Known Limitations row**: "Integer ports only in `line_add` | SPS physical ports (`LConn1`, `RConn1`) cannot be connected." — Stale after F-003 (physical ports now supported via string port names, confirmed PASS in Phase 3).
  3. **Known Limitations row**: "Single parameter per `set_param` | Interdependent parameters fail on intermediate state." — Stale after F-006 (atomic multi-param now supported, confirmed PASS in Phase 3).
  4. **Known Limitations row**: "No arbitrary MATLAB execution | Complex operations not reachable. | Pending `run_matlab` action (backlog F-001)" — Stale after F-001 (`matlab_eval` shipped in v2.6.0, though currently broken by FAIL-003).
- **Expected**: Known Limitations reflects current capability boundaries.
- **Actual**: Three resolved limitations still appear as active constraints; single-param note contradicts shipped multi-param feature.
- **Commit**: 31245ca

### [RESOLVED in 3f63378] FAIL-005: reference.md line_add signal success shape is inaccurate
- **Phase**: Phase 5 (Documentation)
- **File**: `skills/simulink_automation/reference.md`
- **Steps**:
  ```
  python -m simulink_cli --json '{"action":"line_add","model":"LiveTest29E","src_block":"Sine1","src_port":1,"dst_block":"Gain1","dst_port":1}'
  ```
- **Expected** (per reference.md):
  ```json
  {"action":"line_add","model":"my_model","src_block":"Sine","src_port":1,"dst_block":"Gain","dst_port":1,"verified":true,"rollback":{...}}
  ```
- **Actual**:
  ```json
  {"action":"line_add","model":"LiveTest29E","line_handle":1457.0,"verified":true,"rollback":{"action":"line_delete","model":"LiveTest29E","src_block":"Sine1","src_port":1,"dst_block":"Gain1","dst_port":1,"available":true}}
  ```
  `src_block`, `src_port`, `dst_block`, `dst_port` are NOT in the top-level response. They appear only in the `rollback` payload. The `line_handle` field is present but not shown in the documented shape.
- **Commit**: 31245ca

## Blocked Details

None.

## Suggestions

### Bug Fixes
- **FAIL-002 fix**: In `block_add`, convert the `position` Python list to a MATLAB double array before calling `set_param`. Use `matlab.double([l, t, r, b])` or `eng.set_param(dst, 'Position', matlab.double(position))`. The current code likely passes a raw Python list, which MATLAB rejects as an invalid Position type.
- **FAIL-003 fix**: Replace `evalc_async` with `evalc` (synchronous) in both `model_update` (I-003 diagnostics path) and `matlab_eval` (F-001). `evalc(cmd)` captures command output to a string — it is the standard MATLAB function for this purpose. Alternatively, if async behavior was intended for non-blocking execution, the implementation must ship the helper function alongside the CLI or use a well-known pattern.

### Documentation Fixes
- **FAIL-004 fix**: Update `skills/simulink_automation/SKILL.md`:
  1. Remove or update line 37 — replace "One parameter per `set_param` invocation" with a note that both single-param (`param`/`value`) and multi-param (`params`) modes are supported.
  2. Remove the three now-resolved Known Limitations rows (physical port, single-param, no arbitrary MATLAB execution). If matlab_eval remains broken (FAIL-003), restore the "no arbitrary MATLAB execution" row until FAIL-003 is fixed.
- **FAIL-005 fix**: Update `skills/simulink_automation/reference.md` standard `line_add` success shape:
  - Remove `src_block`, `src_port`, `dst_block`, `dst_port` from the top-level response object.
  - Add `line_handle` to the documented shape (it is present in every actual response).
  - These fields belong only to the `rollback` payload, which the reference already shows correctly in the physical port shape.

### Optimization
- **simulate HTML warnings**: The `simulate` (and likely `model_update`) `warnings` array contains MATLAB HTML anchor tags (`<a href="matlab:...">`). These are not meaningful in a CLI/agent context. Consider stripping HTML from warning strings before embedding in JSON. (Carried forward from v2.5.0 report.)
- **block_add rollback source**: `block_delete` rollback notes `available: false` without persisting original source path. Adding source path persistence would make rollback actionable. (Carried forward from v2.5.0 report.)

### Missing Features
- **simulate output data**: `simulate` runs successfully but returns only warnings. There is no way to retrieve workspace variables or logged signal data via CLI. Useful for closed-loop control validation workflows.
- **model_update diagnostics** (blocked by FAIL-003): The `diagnostics` field in `model_update` response is documented in reference.md but cannot be verified until `evalc_async` is resolved.
- **matlab_eval output** (blocked by FAIL-003): F-001 feature is fully specified and documented but non-functional on this device. Post-FAIL-003-fix test required.

## Run History
| Date | Mode | Commit | Result | Notes |
|------|------|--------|--------|-------|
| 2026-03-24 | full | 7244e65 | ✅ 20/20 PASS | Initial full test, v2.2.0 |
| 2026-03-26 | full | 1671c0a | ⚠️ 36/37 PASS | Full test v2.5.0; FAIL-001 stdout contamination |
| 2026-03-29 | full | 31245ca | ⚠️ 38/43 PASS | Full test v2.7.0; FAIL-001 resolved; FAIL-002 block_add position; FAIL-003 evalc_async (model_update + matlab_eval); FAIL-004/005 doc accuracy |
| 2026-03-29 | incremental | 00ef2f9 | ✅ 43/43 PASS | Retest v2.7.1; FAIL-002/003/004/005 all resolved in 3f63378 |

## Schema Snapshot
```json
{"version": "2.7", "actions": {"schema": {"description": "Return machine-readable command contract and error-code catalog.", "fields": {}}, "scan": {"description": "Read model or subsystem topology with optional hierarchy view.", "fields": {"model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."}, "subsystem": {"type": "string", "required": false, "default": null, "description": "Optional subsystem path under model."}, "recursive": {"type": "boolean", "required": false, "default": false, "description": "Recursively scan all nested blocks under scan root."}, "hierarchy": {"type": "boolean", "required": false, "default": false, "description": "Include hierarchy tree in output (implies recursive)."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}, "max_blocks": {"type": "integer", "required": false, "default": null, "description": "Limit number of block entries returned."}, "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected block fields to include."}}}, "connections": {"description": "Read upstream/downstream block relationships from a target block.", "fields": {"model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."}, "target": {"type": "string", "required": true, "default": null, "description": "Block path to analyze."}, "direction": {"type": "string", "required": false, "default": "both", "enum": ["upstream", "downstream", "both"], "description": "Traversal direction from target block."}, "depth": {"type": "integer", "required": false, "default": 1, "description": "Traversal depth in hops."}, "detail": {"type": "string", "required": false, "default": "summary", "enum": ["summary", "ports", "lines"], "description": "Output detail level."}, "include_handles": {"type": "boolean", "required": false, "default": false, "description": "Include line handles in lines detail output."}, "max_edges": {"type": "integer", "required": false, "default": null, "description": "Limit number of connection edges returned."}, "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected top-level response fields to include."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}}}, "highlight": {"description": "Highlight a target block in Simulink UI.", "fields": {"target": {"type": "string", "required": true, "default": null, "description": "Block path to highlight."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}}}, "inspect": {"description": "Read block parameters and effective values.", "fields": {"model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."}, "target": {"type": "string", "required": true, "default": null, "description": "Block path to inspect."}, "param": {"type": "string", "required": false, "default": "All", "description": "Parameter name to read, or All for dialog parameters."}, "active_only": {"type": "boolean", "required": false, "default": false, "description": "Return only active parameters when param=All."}, "strict_active": {"type": "boolean", "required": false, "default": false, "description": "Fail when requested parameter is inactive."}, "resolve_effective": {"type": "boolean", "required": false, "default": false, "description": "Resolve known effective value for inactive parameter."}, "summary": {"type": "boolean", "required": false, "default": false, "description": "Include compact summary lists when param=All."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}, "max_params": {"type": "integer", "required": false, "default": null, "description": "Limit number of parameters returned when param=All."}, "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected top-level response fields to include."}}}, "find": {"description": "Search for blocks by name pattern and/or block type.", "fields": {"model": {"type": "string", "required": false, "default": null, "description": "Target model (same resolution as scan)."}, "subsystem": {"type": "string", "required": false, "default": null, "description": "Narrow search scope to a subsystem."}, "name": {"type": "string", "required": false, "default": null, "description": "Name substring match (case-insensitive)."}, "block_type": {"type": "string", "required": false, "default": null, "description": "BlockType exact match (e.g., SubSystem, Gain)."}, "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}, "max_results": {"type": "integer", "required": false, "default": 200, "description": "Limit number of results returned."}, "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected result fields to include."}}}, "list_opened": {"description": "List currently opened Simulink models.", "fields": {"session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}}}, "set_param": {"description": "Set a block parameter with dry-run preview and rollback support.", "fields": {"target": {"type": "string", "required": true, "default": null, "description": "Full block path to modify."}, "param": {"type": "string", "required": false, "default": null, "description": "Parameter name (mutually exclusive with 'params')."}, "value": {"type": "string", "required": false, "default": null, "description": "New parameter value (mutually exclusive with 'params')."}, "params": {"type": "object", "required": false, "default": null, "description": "Multiple parameter-value pairs for atomic update (mutually exclusive with 'param'/'value')."}, "expected_current_value": {"type": "string", "required": false, "default": null, "description": "Optional guarded-execute precondition from a single-param dry-run preview."}, "expected_current_values": {"type": "object", "required": false, "default": null, "description": "Optional guarded-execute precondition from a multi-param dry-run preview."}, "dry_run": {"type": "boolean", "required": false, "default": true, "description": "Preview mode — show diff without writing. Defaults to true."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "session": {"description": "Manage active MATLAB shared session selection.", "fields": {"session_action": {"type": "string", "required": true, "default": null, "enum": ["list", "use", "current", "clear"], "description": "Session management operation.", "positional": true}, "name": {"type": "string", "required": false, "default": null, "description": "Session name, required when session_action=use.", "positional_optional": true}}}, "model_new": {"description": "Create a new Simulink model.", "fields": {"name": {"type": "string", "required": true, "default": null, "description": "Name for the new model."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "model_open": {"description": "Open a Simulink model from file path or MATLAB path.", "fields": {"path": {"type": "string", "required": true, "default": null, "description": "File path or model name to open."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "model_save": {"description": "Save a loaded Simulink model to disk.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Name of the loaded model to save."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "model_close": {"description": "Close a loaded Simulink model.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Model name to close."}, "force": {"type": "boolean", "required": false, "default": false, "description": "Close even if model has unsaved changes."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "model_update": {"description": "Compile/update a loaded Simulink model diagram.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Model name to update/compile."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "block_add": {"description": "Add a block to a loaded Simulink model.", "fields": {"source": {"type": "string", "required": true, "default": null, "description": "Library source path (e.g. 'simulink/Math Operations/Gain'). Some library categories contain literal newlines in the path (e.g. 'simulink/Signal\\nRouting/Mux'); use JSON \\n escape. The library root is auto-loaded on first use."}, "destination": {"type": "string", "required": true, "default": null, "description": "Full block path in model (e.g. 'my_model/Gain1')."}, "position": {"type": "array", "items": "number", "required": false, "default": null, "description": "Block position as [left, top, right, bottom] in pixels (e.g. [50, 100, 130, 130])."}, "auto_layout": {"type": "boolean", "required": false, "default": false, "description": "Run Simulink.BlockDiagram.arrangeSystem on the parent model after adding the block."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "block_delete": {"description": "Delete a block from a loaded Simulink model.", "fields": {"destination": {"type": "string", "required": true, "default": null, "description": "Full block path in model (e.g. 'my_model/Gain1')."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "line_add": {"description": "Connect two block ports with a signal line.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Target model or subsystem path."}, "src_block": {"type": "string", "required": true, "default": null, "description": "Source block name (local to model, must not contain '/')."}, "src_port": {"type": "port", "required": true, "default": null, "description": "Source port — integer (signal) or string name (physical, e.g. 'RConn1')."}, "dst_block": {"type": "string", "required": true, "default": null, "description": "Destination block name (local to model, must not contain '/')."}, "dst_port": {"type": "port", "required": true, "default": null, "description": "Destination port — integer (signal) or string name (physical, e.g. 'LConn1')."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "line_delete": {"description": "Delete a signal line between two block ports.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Target model or subsystem path."}, "src_block": {"type": "string", "required": true, "default": null, "description": "Source block name (local to model, must not contain '/')."}, "src_port": {"type": "port", "required": true, "default": null, "description": "Source port — integer (signal) or string name (physical, e.g. 'RConn1')."}, "dst_block": {"type": "string", "required": true, "default": null, "description": "Destination block name (local to model, must not contain '/')."}, "dst_port": {"type": "port", "required": true, "default": null, "description": "Destination port — integer (signal) or string name (physical, e.g. 'LConn1')."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "simulate": {"description": "Run simulation on a loaded Simulink model.", "fields": {"model": {"type": "string", "required": true, "default": null, "description": "Model name to simulate."}, "stop_time": {"type": "number", "required": false, "default": null, "description": "Override simulation stop time (seconds). Does not modify the model."}, "max_step": {"type": "number", "required": false, "default": null, "description": "Override solver maximum step size (seconds). Does not modify the model."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}, "matlab_eval": {"description": "Execute arbitrary MATLAB code and return captured text output.", "fields": {"code": {"type": "string", "required": true, "default": null, "description": "MATLAB code to execute. Supports multi-line."}, "timeout": {"type": "number", "required": false, "default": 30, "description": "Execution timeout in seconds. Prevents runaway code."}, "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}}}}, "error_codes": ["block_already_exists", "block_not_found", "engine_unavailable", "eval_failed", "eval_timeout", "inactive_parameter", "invalid_input", "invalid_json", "invalid_subsystem_type", "json_conflict", "line_already_exists", "line_not_found", "model_already_loaded", "model_dirty", "model_not_found", "model_required", "model_save_failed", "no_session", "param_not_found", "port_not_found", "precondition_failed", "runtime_error", "session_not_found", "session_required", "set_param_failed", "simulation_failed", "source_not_found", "state_clear_failed", "state_write_failed", "subsystem_not_found", "unknown_parameter", "update_failed", "verification_failed"]}
```
