# Live Test Report

## Meta
| Field | Value |
|-------|-------|
| Plugin Version | 2.2.0 |
| Test Date | 2026-03-24 14:30 |
| Test Commit | 7244e65 |
| Test Mode | full |
| MATLAB Version | MATLAB_257680 (shared session) |
| Simulink Version | N/A (session list only) |

## Summary
| Total | Pass | Fail | Blocked | Skip |
|-------|------|------|---------|------|
| 20    | 20   | 0    | 0       | 0    |

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
| 1 | schema action | PASS | 7244e65 | Returns valid JSON with version 2.2, 12 actions, 24 error codes |
| 2 | session list | PASS | 7244e65 | Returns MATLAB_257680 as active session |
| 3 | list_opened | PASS | 7244e65 | Returns 11 opened models |

### Phase 2: Read-Only
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | scan (model=simulink) | PASS | 7244e65 | Returns 23 blocks, truncated=false |
| 2 | find (block_type=SubSystem) | PASS | 7244e65 | Returns 411 results, truncated=true with warning |
| 3 | inspect (specific param) | PASS | 7244e65 | Returns value="Observer" for Constant Value param |
| 4 | connections (downstream) | PASS | 7244e65 | Returns valid summary with upstream/downstream arrays |
| 5 | highlight | PASS | 7244e65 | Returns success status, highlighted target |

### Phase 3: Lifecycle & Write
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | model_new | PASS | 7244e65 | Creates LiveTestModel, appears in list_opened |
| 2 | model_save | PASS | 7244e65 | Saves model successfully |
| 3 | set_param (dry_run=true) | PASS | 7244e65 | Returns current_value, proposed_value, apply_payload, rollback |
| 4 | set_param (dry_run=false) | PASS | 7244e65 | write_state=verified, verified=true |
| 5 | set_param read-back | PASS | 7244e65 | Value confirmed changed to TestValue via inspect |
| 6 | set_param rollback | PASS | 7244e65 | Value restored to Observer |

### Phase 4: Error Handling
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | Missing required field (model) | PASS | 7244e65 | Returns model_required with suggested_fix |
| 2 | Unknown parameter | PASS | 7244e65 | Returns unknown_parameter with cause |
| 3 | Unknown action | PASS | 7244e65 | Returns invalid_json with cause |
| 4 | Wrong parameter type | PASS | 7244e65 | Returns invalid_json with must be boolean |
| 5 | model_not_found | PASS | 7244e65 | Returns model_not_found with list of open models |
| 6 | block_not_found | PASS | 7244e65 | Returns block_not_found with suggested_fix |

### Phase 5: Documentation
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | SKILL.md session action syntax | PASS | 7244e65 | Schema confirms session_action field, not sub_action |
| 2 | Write safety model (dry_run) | PASS | 7244e65 | dry_run=true returns apply_payload + rollback |
| 3 | Error code recovery routing | PASS | 7244e65 | model_not_found, block_not_found match docs |
| 4 | Output discipline | PASS | 7244e65 | All responses valid JSON, no raw text |

## Failure Details

None.

## Blocked Details

None.

## Suggestions

### Bug Fixes
None required - all tests passed.

### Optimization
- **find action warning**: The find action returns a warning about Variant Subsystem handling. This is informational but clutters output. Consider filtering warnings or adding a variant-aware mode.

### Missing Features
- **model_close**: The skill documentation notes model_close is not implemented. Users cannot close models via CLI, requiring manual MATLAB close. Consider adding model_close action.

## Run History
| Date | Mode | Commit | Result | Notes |
|------|------|--------|--------|-------|
| 2026-03-24 | full | 7244e65 | ✅ 20/20 PASS | Initial full test |

## Schema Snapshot
```json
{
  "version": "2.2",
  "actions": {
    "schema": {
      "description": "Return machine-readable command contract and error-code catalog.",
      "fields": {}
    },
    "scan": {
      "description": "Read model or subsystem topology with optional hierarchy view.",
      "fields": {
        "model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."},
        "subsystem": {"type": "string", "required": false, "default": null, "description": "Optional subsystem path under model."},
        "recursive": {"type": "boolean", "required": false, "default": false, "description": "Recursively scan all nested blocks under scan root."},
        "hierarchy": {"type": "boolean", "required": false, "default": false, "description": "Include hierarchy tree in output (implies recursive)."},
        "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."},
        "max_blocks": {"type": "integer", "required": false, "default": null, "description": "Limit number of block entries returned."},
        "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected block fields to include."}
      }
    },
    "connections": {
      "description": "Read upstream/downstream block relationships from a target block.",
      "fields": {
        "model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."},
        "target": {"type": "string", "required": true, "default": null, "description": "Block path to analyze."},
        "direction": {"type": "string", "required": false, "default": "both", "enum": ["upstream", "downstream", "both"], "description": "Traversal direction from target block."},
        "depth": {"type": "integer", "required": false, "default": 1, "description": "Traversal depth in hops."},
        "detail": {"type": "string", "required": false, "default": "summary", "enum": ["summary", "ports", "lines"], "description": "Output detail level."},
        "include_handles": {"type": "boolean", "required": false, "default": false, "description": "Include line handles in lines detail output."},
        "max_edges": {"type": "integer", "required": false, "default": null, "description": "Limit number of connection edges returned."},
        "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected top-level response fields to include."},
        "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}
      }
    },
    "highlight": {
      "description": "Highlight a target block in Simulink UI.",
      "fields": {
        "target": {"type": "string", "required": true, "default": null, "description": "Block path to highlight."},
        "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}
      }
    },
    "inspect": {
      "description": "Read block parameters and effective values.",
      "fields": {
        "model": {"type": "string", "required": false, "default": null, "description": "Optional specific model name from list_opened output."},
        "target": {"type": "string", "required": true, "default": null, "description": "Block path to inspect."},
        "param": {"type": "string", "required": false, "default": "All", "description": "Parameter name to read, or All for dialog parameters."},
        "active_only": {"type": "boolean", "required": false, "default": false, "description": "Return only active parameters when param=All."},
        "strict_active": {"type": "boolean", "required": false, "default": false, "description": "Fail when requested parameter is inactive."},
        "resolve_effective": {"type": "boolean", "required": false, "default": false, "description": "Resolve known effective value for inactive parameter."},
        "summary": {"type": "boolean", "required": false, "default": false, "description": "Include compact summary lists when param=All."},
        "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."},
        "max_params": {"type": "integer", "required": false, "default": null, "description": "Limit number of parameters returned when param=All."},
        "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected top-level response fields to include."}
      }
    },
    "find": {
      "description": "Search for blocks by name pattern and/or block type.",
      "fields": {
        "model": {"type": "string", "required": false, "default": null, "description": "Target model (same resolution as scan)."},
        "subsystem": {"type": "string", "required": false, "default": null, "description": "Narrow search scope to a subsystem."},
        "name": {"type": "string", "required": false, "default": null, "description": "Name substring match (case-insensitive)."},
        "block_type": {"type": "string", "required": false, "default": null, "description": "BlockType exact match (e.g., SubSystem, Gain)."},
        "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."},
        "max_results": {"type": "integer", "required": false, "default": 200, "description": "Limit number of results returned."},
        "fields": {"type": "array", "items": "string", "required": false, "default": null, "description": "Projected result fields to include."}
      }
    },
    "list_opened": {
      "description": "List currently opened Simulink models.",
      "fields": {
        "session": {"type": "string", "required": false, "default": null, "description": "Session override for this command."}
      }
    },
    "set_param": {
      "description": "Set a block parameter with dry-run preview and rollback support.",
      "fields": {
        "target": {"type": "string", "required": true, "default": null, "description": "Full block path to modify."},
        "param": {"type": "string", "required": true, "default": null, "description": "Parameter name."},
        "value": {"type": "string", "required": true, "default": null, "description": "New parameter value (always string — MATLAB handles conversion)."},
        "expected_current_value": {"type": "string", "required": false, "default": null, "description": "Optional guarded-execute precondition from a dry-run preview."},
        "dry_run": {"type": "boolean", "required": false, "default": true, "description": "Preview mode — show diff without writing. Defaults to true."},
        "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}
      }
    },
    "session": {
      "description": "Manage active MATLAB shared session selection.",
      "fields": {
        "session_action": {"type": "string", "required": true, "default": null, "enum": ["list", "use", "current", "clear"], "description": "Session management operation.", "positional": true},
        "name": {"type": "string", "required": false, "default": null, "description": "Session name, required when session_action=use.", "positional_optional": true}
      }
    },
    "model_new": {
      "description": "Create a new Simulink model.",
      "fields": {
        "name": {"type": "string", "required": true, "default": null, "description": "Name for the new model."},
        "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}
      }
    },
    "model_open": {
      "description": "Open a Simulink model from file path or MATLAB path.",
      "fields": {
        "path": {"type": "string", "required": true, "default": null, "description": "File path or model name to open."},
        "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}
      }
    },
    "model_save": {
      "description": "Save a loaded Simulink model to disk.",
      "fields": {
        "model": {"type": "string", "required": true, "default": null, "description": "Name of the loaded model to save."},
        "session": {"type": "string", "required": false, "default": null, "description": "MATLAB session name override."}
      }
    }
  },
  "error_codes": [
    "block_not_found",
    "engine_unavailable",
    "inactive_parameter",
    "invalid_input",
    "invalid_json",
    "invalid_subsystem_type",
    "json_conflict",
    "model_already_loaded",
    "model_not_found",
    "model_required",
    "model_save_failed",
    "no_session",
    "param_not_found",
    "precondition_failed",
    "runtime_error",
    "session_not_found",
    "session_required",
    "set_param_failed",
    "state_clear_failed",
    "state_write_failed",
    "subsystem_not_found",
    "unknown_parameter",
    "verification_failed"
  ]
}
```
