# v2.3.0 Block Placement Design

Status: Approved (2026-03-25)

## Goal

AI can add blocks to a loaded Simulink model. This is Phase 1's third sub-phase, enabling the first structural edit capability. After this, models can contain actual blocks — not just be empty shells.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Position parameter | Omitted | MATLAB auto-places; `set_param` can adjust afterward; `line_add` (v2.4) uses port names, not coordinates; `Simulink.BlockDiagram.arrangeSystem` handles layout |
| Field naming | `source` + `destination` | Consistent with existing action naming style; description fields clarify semantics |
| Source validation | Precondition via `get_param(source, "Handle")` | Structural check, no error-text parsing; MATLAB version changes don't affect logic |
| Safety tier | Checked Mutation | Matches roadmap; no dry_run ceremony, yes precondition/verify/rollback |

## Action Schema

```python
# simulink_cli/actions/block_cmd.py

DESCRIPTION = "Add a block to a loaded Simulink model."

FIELDS = {
    "source":      {"type": "string", "required": True,  "default": None,
                    "description": "Library source path (e.g. 'simulink/Math Operations/Gain')."},
    "destination": {"type": "string", "required": True,  "default": None,
                    "description": "Full block path in model (e.g. 'my_model/Gain1')."},
    "session":     {"type": "string", "required": False, "default": None,
                    "description": "MATLAB session name override."},
}

ERRORS = [
    "engine_unavailable", "no_session", "session_not_found", "session_required",
    "model_not_found", "source_not_found", "block_already_exists",
    "verification_failed", "runtime_error",
]
```

## Execute Flow

```
1. CONNECT — safe_connect_to_session(session)
   Failure → engine_unavailable / no_session / session_not_found / session_required

2. PRECONDITION: parent model is loaded
   get_param(model_root, "Handle")    # model_root = destination.split("/")[0]
   Failure → model_not_found

3. PRECONDITION: source library block exists
   get_param(source, "Handle")
   Failure → source_not_found

4. PRECONDITION: destination does not already exist
   get_param(destination, "Handle")
   Success → block_already_exists (occupied, error)
   Failure → expected, continue

5. EXECUTE
   add_block(source, destination)
   Exception → runtime_error + details.cause

6. VERIFY — read-back confirmation
   get_param(destination, "Handle")
   Failure → verification_failed

7. Build rollback payload (available: false, activated in Phase 3)

8. Return success response
```

## Success Response

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

## Transport Layer

One addition to `matlab_transport.py`:

```python
def add_block(engine, source, dest):
    return call_no_output(engine, "add_block", source, dest)
```

## Fake Engine

New `FakeBlockEngine` in `tests/fakes.py`:

```python
class FakeBlockEngine:
    def __init__(self, loaded_models=None, blocks=None, library_sources=None):
        self._loaded = set(loaded_models or [])
        self._blocks = set(blocks or [])
        self._library_sources = set(library_sources or [])

    def get_param(self, target, param, nargout=1):
        if target in self._library_sources and param == "Handle":
            return 1.0
        if target in self._loaded and param == "Handle":
            return 1.0
        if target in self._blocks and param == "Handle":
            return 1.0
        raise RuntimeError(f"Invalid Simulink object name: {target}")

    def add_block(self, source, dest, nargout=0):
        model_root = dest.split("/")[0]
        if model_root not in self._loaded:
            raise RuntimeError("Model not loaded")
        if dest in self._blocks:
            raise RuntimeError("Block already exists")
        self._blocks.add(dest)
```

## Behavior Tests

File: `tests/test_block_cmd_behavior.py`

| Test Case | Expected |
|-----------|----------|
| Happy path: valid source, destination doesn't exist | `verified: true`, no error |
| Parent model not loaded | `error: model_not_found` |
| Source doesn't exist in library | `error: source_not_found` |
| Destination already exists | `error: block_already_exists` |
| `add_block` runtime exception | `error: runtime_error` |
| Verify fails after execute | `error: verification_failed` |
| Rollback payload structure | `available: false`, action is `block_delete` |
| Session passes through to rollback | rollback contains session field |
| Validate: missing source | `error: invalid_input` |
| Validate: missing destination | `error: invalid_input` |

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `simulink_cli/actions/block_cmd.py` | Action module |
| `tests/test_block_cmd_behavior.py` | Behavior tests |

### Modified Files

| File | Change |
|------|--------|
| `simulink_cli/core.py` | Import block_cmd, register `"block_add": block_cmd`, version → `"2.3"` |
| `simulink_cli/actions/__init__.py` | No change needed — file is empty; `core.py` imports modules directly |
| `simulink_cli/matlab_transport.py` | Add `add_block()` transport function |
| `tests/fakes.py` | Add `FakeBlockEngine` |
| `tests/test_schema_action.py` | Add `"block_add"` to expected set, version → `"2.3"` |
| `tests/test_docs_contract.py` | Assert `source_not_found`, `block_already_exists` in recovery routing |
| `skills/simulink_automation/SKILL.md` | Add block_add to Direct Handling; add new error codes to Recovery Routing |
| `skills/simulink_automation/reference.md` | Add block_add response shapes |
| `.claude-plugin/plugin.json` | Version → `2.3.0` |
| `.claude-plugin/marketplace.json` | Version → `2.3.0` |
| `README.md` | Add block_add description |
| `README.zh-CN.md` | Add block_add description |

## What This Design Does NOT Cover

- Block position/coordinates (use `set_param` after placement)
- `block_delete` (Phase 3)
- Batch block creation (post-Phase 3)
- Library browser / block discovery (use `find` action with library paths)
