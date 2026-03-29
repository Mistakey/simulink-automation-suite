# Live Test Report

## Meta
| Field | Value |
|-------|-------|
| Plugin Version | 2.9.0 (pre-release) |
| Test Date | 2026-03-29 |
| Test Commit | 06682ab |
| Test Mode | incremental |
| MATLAB Version | MATLAB_257680 (shared session) |
| Simulink Version | N/A (session list only) |

## Summary
| Total | Pass | Fail | Blocked | Skip |
|-------|------|------|---------|------|
| 56    | 56   | 0    | 0       | 0    |

Phase Coverage:
| Phase | Status |
|-------|--------|
| 0 Environment | ✅ PASS |
| 1 Meta | ✅ PASS |
| 2 Read-Only | ✅ PASS (carried) |
| 3 Lifecycle & Write | ✅ PASS |
| 4 Error Handling | ✅ PASS |
| 5 Documentation | ✅ PASS (carried) |

## Results

### Phase 1: Meta
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | schema action | PASS | b2e43fc | Returns v2.9, 22 actions, 35 error codes (was v2.7/20/33) |
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
| 1 | model_new (LiveTest29G) | PASS | b2e43fc | verified=true; appears in list_opened |
| 2 | model_copy (LiveTest29G → LiveTest29G_copy) | PASS | 06682ab | Fixed in 06682ab: uses copyfile instead of save_system |
| 3 | block_add (basic, no position) | PASS | 31245ca | verified=true; rollback payload present |
| 4 | block_add (position=[50,50,130,80]) | PASS | 00ef2f9 | Fixed in 3f63378: position field present in response; verified=true |
| 5 | block_add (auto_layout=true) | PASS | 31245ca | verified=true; auto_layout accepted and applied |
| 6 | block_add batch (3 blocks) | PASS | b2e43fc | completed=3, total=3, all verified=true |
| 7 | block_add batch stop-on-failure | PASS | b2e43fc | completed=1, total=3, error at index 1 (source_not_found) |
| 8 | block_add source_not_found suggestions | PASS | b2e43fc | suggestions field present with similar library paths |
| 9 | line_add (signal, integer ports) | PASS | 31245ca | Returns line_handle, verified=true, rollback present |
| 10 | line_add batch (2 lines) | PASS | b2e43fc | completed=2, total=2, all verified=true |
| 11 | set_param single dry_run=true | PASS | 31245ca | Returns current_value, proposed_value, apply_payload, rollback |
| 12 | set_param multi-param dry_run=true (F-006) | PASS | 31245ca | Returns changes array with expected_current_values in apply_payload |
| 13 | set_param single dry_run=false | PASS | 31245ca | write_state=verified, new_value=10 |
| 14 | set_param multi-param dry_run=false (F-006) | PASS | 31245ca | write_state=verified; changes with previous_value/new_value per param |
| 15 | set_param read-back via inspect | PASS | 31245ca | Gain=10 confirmed via inspect |
| 16 | model_update | PASS | 00ef2f9 | Fixed in 3f63378: returns diagnostics=[] + warnings array |
| 17 | simulate (stop_time, max_step overrides) | PASS | 31245ca | Returns overrides field with StopTime/MaxStep |
| 18 | simulate (timeout parameter) | PASS | b2e43fc | timeout=30 in response, overrides present |
| 19 | simulate workspace storage (sl_sim_result) | PASS | b2e43fc | matlab_eval confirms exist('sl_sim_result','var')=1 after simulate |
| 20 | model_save | PASS | 31245ca | Returns success envelope |
| 21 | model_close (dirty — expect error) | PASS | 31245ca | Returns model_dirty with suggested_fix |
| 22 | model_close (force=true) | PASS | 31245ca | Model closed successfully |
| 23 | matlab_eval (F-001) | PASS | 00ef2f9 | Fixed in 3f63378: output="    42\n\n", truncated=false, warnings=[] |
| 24 | line_add physical port RConn1/LConn1 (F-003) | PASS | 31245ca | Returns line_handle, verified=true; rollback payload preserves string port names |
| 25 | line_delete physical port RConn1/LConn1 (F-003) | PASS | 31245ca | Returns rollback with line_add and string port names |

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
| 8 | precondition_failed (multi-param, F-006) | PASS | 31245ca | Returns precondition_failed, write_state=not_attempted |
| 9 | block_add invalid path → runtime_error | PASS | 31245ca | Returns runtime_error with cause detail |
| 10 | model_copy source not loaded | PASS | b2e43fc | Returns model_not_found with suggested_fix |
| 11 | simulate invalid timeout (-5) | PASS | b2e43fc | Returns invalid_input "must be a positive number" |
| 12 | block_add batch empty array | PASS | b2e43fc | Returns invalid_input "must be a non-empty array" |
| 13 | block_add batch+source mutual exclusion | PASS | b2e43fc | Returns invalid_input "mutually exclusive" |

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

### [RESOLVED in 06682ab] FAIL-001: model_copy renames loaded model instead of creating independent copy
- **Phase**: Phase 3 (Lifecycle & Write)
- **Action**: `model_copy`
- **Root Cause**: `save_system('src', 'dest')` in MATLAB is a "save as" operation that renames the loaded model.
- **Fix**: Switched to `save_system` + `copyfile` approach — saves source to disk first, then copies the .slx file. Model name is never changed.

## Blocked Details

None.

## Suggestions

### Bug Fixes
- None — all bugs resolved.

### Optimization
- **simulate HTML warnings**: The `simulate` `warnings` array contains MATLAB HTML anchor tags (`<a href="matlab:...">`). Not meaningful in CLI/agent context. Consider stripping HTML. (Carried forward.)

### Missing Features
- None — all backlog items implemented and verified.

## Run History
| Date | Mode | Commit | Result | Notes |
|------|------|--------|--------|-------|
| 2026-03-24 | full | 7244e65 | ✅ 20/20 PASS | Initial full test, v2.2.0 |
| 2026-03-26 | full | 1671c0a | ⚠️ 36/37 PASS | Full test v2.5.0; FAIL-001 stdout contamination |
| 2026-03-29 | full | 31245ca | ⚠️ 38/43 PASS | Full test v2.7.0; FAIL-001 resolved; FAIL-002/003/004/005 |
| 2026-03-29 | incremental | 00ef2f9 | ✅ 43/43 PASS | Retest v2.7.1; all FAILs resolved |
| 2026-03-29 | incremental | b2e43fc | ⚠️ 55/56 PASS | v2.9.0 pre-release; FAIL-001 model_copy rename; 13 new tests |
| 2026-03-29 | targeted | 06682ab | ✅ 56/56 PASS | FAIL-001 resolved: model_copy uses copyfile |

## Schema Snapshot
```json
{"version":"2.9","actions":{"schema":{"description":"Return machine-readable command contract and error-code catalog.","fields":{}},"scan":{"description":"Read model or subsystem topology with optional hierarchy view.","fields":{"model":{"type":"string","required":false,"default":null,"description":"Optional specific model name from list_opened output."},"subsystem":{"type":"string","required":false,"default":null,"description":"Optional subsystem path under model."},"recursive":{"type":"boolean","required":false,"default":false,"description":"Recursively scan all nested blocks under scan root."},"hierarchy":{"type":"boolean","required":false,"default":false,"description":"Include hierarchy tree in output (implies recursive)."},"session":{"type":"string","required":false,"default":null,"description":"Session override for this command."},"max_blocks":{"type":"integer","required":false,"default":null,"description":"Limit number of block entries returned."},"fields":{"type":"array","items":"string","required":false,"default":null,"description":"Projected block fields to include."}}},"connections":{"description":"Read upstream/downstream block relationships from a target block.","fields":{"model":{"type":"string","required":false,"default":null,"description":"Optional specific model name from list_opened output."},"target":{"type":"string","required":true,"default":null,"description":"Block path to analyze."},"direction":{"type":"string","required":false,"default":"both","enum":["upstream","downstream","both"],"description":"Traversal direction from target block."},"depth":{"type":"integer","required":false,"default":1,"description":"Traversal depth in hops."},"detail":{"type":"string","required":false,"default":"summary","enum":["summary","ports","lines"],"description":"Output detail level."},"include_handles":{"type":"boolean","required":false,"default":false,"description":"Include line handles in lines detail output."},"max_edges":{"type":"integer","required":false,"default":null,"description":"Limit number of connection edges returned."},"fields":{"type":"array","items":"string","required":false,"default":null,"description":"Projected top-level response fields to include."},"session":{"type":"string","required":false,"default":null,"description":"Session override for this command."}}},"highlight":{"description":"Highlight a target block in Simulink UI.","fields":{"target":{"type":"string","required":true,"default":null,"description":"Block path to highlight."},"session":{"type":"string","required":false,"default":null,"description":"Session override for this command."}}},"inspect":{"description":"Read block parameters and effective values.","fields":{"model":{"type":"string","required":false,"default":null,"description":"Optional specific model name from list_opened output."},"target":{"type":"string","required":true,"default":null,"description":"Block path to inspect."},"param":{"type":"string","required":false,"default":"All","description":"Parameter name to read, or All for dialog parameters."},"active_only":{"type":"boolean","required":false,"default":false,"description":"Return only active parameters when param=All."},"strict_active":{"type":"boolean","required":false,"default":false,"description":"Fail when requested parameter is inactive."},"resolve_effective":{"type":"boolean","required":false,"default":false,"description":"Resolve known effective value for inactive parameter."},"summary":{"type":"boolean","required":false,"default":false,"description":"Include compact summary lists when param=All."},"session":{"type":"string","required":false,"default":null,"description":"Session override for this command."},"max_params":{"type":"integer","required":false,"default":null,"description":"Limit number of parameters returned when param=All."},"fields":{"type":"array","items":"string","required":false,"default":null,"description":"Projected top-level response fields to include."}}},"find":{"description":"Search for blocks by name pattern and/or block type.","fields":{"model":{"type":"string","required":false,"default":null,"description":"Target model (same resolution as scan)."},"subsystem":{"type":"string","required":false,"default":null,"description":"Narrow search scope to a subsystem."},"name":{"type":"string","required":false,"default":null,"description":"Name substring match (case-insensitive)."},"block_type":{"type":"string","required":false,"default":null,"description":"BlockType exact match (e.g., SubSystem, Gain)."},"session":{"type":"string","required":false,"default":null,"description":"Session override for this command."},"max_results":{"type":"integer","required":false,"default":200,"description":"Limit number of results returned."},"fields":{"type":"array","items":"string","required":false,"default":null,"description":"Projected result fields to include."}}},"list_opened":{"description":"List currently opened Simulink models.","fields":{"session":{"type":"string","required":false,"default":null,"description":"Session override for this command."}}},"set_param":{"description":"Set a block parameter with dry-run preview and rollback support.","fields":{"target":{"type":"string","required":true,"default":null,"description":"Full block path to modify."},"param":{"type":"string","required":false,"default":null,"description":"Parameter name (mutually exclusive with 'params')."},"value":{"type":"string","required":false,"default":null,"description":"New parameter value (mutually exclusive with 'params')."},"params":{"type":"object","required":false,"default":null,"description":"Multiple parameter-value pairs for atomic update (mutually exclusive with 'param'/'value')."},"expected_current_value":{"type":"string","required":false,"default":null,"description":"Optional guarded-execute precondition from a single-param dry-run preview."},"expected_current_values":{"type":"object","required":false,"default":null,"description":"Optional guarded-execute precondition from a multi-param dry-run preview."},"dry_run":{"type":"boolean","required":false,"default":true,"description":"Preview mode - show diff without writing. Defaults to true."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"session":{"description":"Manage active MATLAB shared session selection.","fields":{"session_action":{"type":"string","required":true,"default":null,"enum":["list","use","current","clear"],"description":"Session management operation.","positional":true},"name":{"type":"string","required":false,"default":null,"description":"Session name, required when session_action=use.","positional_optional":true}}},"model_new":{"description":"Create a new Simulink model.","fields":{"name":{"type":"string","required":true,"default":null,"description":"Name for the new model."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"model_open":{"description":"Open a Simulink model from file path or MATLAB path.","fields":{"path":{"type":"string","required":true,"default":null,"description":"File path or model name to open."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"model_save":{"description":"Save a loaded Simulink model to disk.","fields":{"model":{"type":"string","required":true,"default":null,"description":"Name of the loaded model to save."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"model_close":{"description":"Close a loaded Simulink model.","fields":{"model":{"type":"string","required":true,"default":null,"description":"Model name to close."},"force":{"type":"boolean","required":false,"default":false,"description":"Close even if model has unsaved changes."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"model_copy":{"description":"Copy a loaded Simulink model to a new file path.","fields":{"source":{"type":"string","required":true,"default":null,"description":"Name of the loaded source model to copy."},"dest":{"type":"string","required":true,"default":null,"description":"Destination file path for the copy (e.g. 'FOC_Basic' or 'C:/models/FOC_v2.slx')."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"model_update":{"description":"Compile/update a loaded Simulink model diagram.","fields":{"model":{"type":"string","required":true,"default":null,"description":"Model name to update/compile."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"block_add":{"description":"Add a block to a loaded Simulink model.","fields":{"source":{"type":"string","required":false,"default":null,"description":"Source block path."},"destination":{"type":"string","required":false,"default":null,"description":"Full block path in model."},"position":{"type":"array","items":"number","required":false,"default":null,"description":"Block position as [left, top, right, bottom] in pixels."},"auto_layout":{"type":"boolean","required":false,"default":false,"description":"Run arrangeSystem after adding."},"blocks":{"type":"array","required":false,"default":null,"description":"Batch mode: array of {source, destination, position?} objects."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"block_delete":{"description":"Delete a block from a loaded Simulink model.","fields":{"destination":{"type":"string","required":true,"default":null,"description":"Full block path in model."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"line_add":{"description":"Connect two block ports with a signal line.","fields":{"model":{"type":"string","required":true,"default":null,"description":"Target model or subsystem path."},"src_block":{"type":"string","required":false,"default":null,"description":"Source block name."},"src_port":{"type":"port","required":false,"default":null,"description":"Source port."},"dst_block":{"type":"string","required":false,"default":null,"description":"Destination block name."},"dst_port":{"type":"port","required":false,"default":null,"description":"Destination port."},"lines":{"type":"array","required":false,"default":null,"description":"Batch mode: array of {src_block, src_port, dst_block, dst_port} objects."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"line_delete":{"description":"Delete a signal line between two block ports.","fields":{"model":{"type":"string","required":true,"default":null,"description":"Target model or subsystem path."},"src_block":{"type":"string","required":true,"default":null,"description":"Source block name."},"src_port":{"type":"port","required":true,"default":null,"description":"Source port."},"dst_block":{"type":"string","required":true,"default":null,"description":"Destination block name."},"dst_port":{"type":"port","required":true,"default":null,"description":"Destination port."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"simulate":{"description":"Run simulation on a loaded Simulink model.","fields":{"model":{"type":"string","required":true,"default":null,"description":"Model name to simulate."},"stop_time":{"type":"number","required":false,"default":null,"description":"Override simulation stop time (seconds)."},"max_step":{"type":"number","required":false,"default":null,"description":"Override solver maximum step size (seconds)."},"timeout":{"type":"number","required":false,"default":null,"description":"Simulation timeout in seconds."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}},"matlab_eval":{"description":"Execute arbitrary MATLAB code and return captured text output.","fields":{"code":{"type":"string","required":true,"default":null,"description":"MATLAB code to execute. Supports multi-line."},"timeout":{"type":"number","required":false,"default":30,"description":"Execution timeout in seconds."},"session":{"type":"string","required":false,"default":null,"description":"MATLAB session name override."}}}},"error_codes":["block_already_exists","block_not_found","engine_unavailable","eval_failed","eval_timeout","inactive_parameter","invalid_input","invalid_json","invalid_subsystem_type","json_conflict","line_already_exists","line_not_found","model_already_loaded","model_copy_failed","model_dirty","model_not_found","model_required","model_save_failed","no_session","param_not_found","port_not_found","precondition_failed","runtime_error","session_not_found","session_required","set_param_failed","simulation_failed","simulation_timeout","source_not_found","state_clear_failed","state_write_failed","subsystem_not_found","unknown_parameter","update_failed","verification_failed"]}
```
