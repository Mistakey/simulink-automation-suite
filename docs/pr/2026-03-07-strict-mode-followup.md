# PR: Strict Mode Follow-up for Agent Safety

## Summary
This PR finishes the strict-mode hardening follow-up for the Simulink CLI/skill, focused on deterministic agent behavior and safer input handling.

## What changed

### 1. Strict session semantics alignment
- Removed misleading "saved session becomes active" behavior when multiple MATLAB sessions exist.
- Multi-session context now requires explicit session selection; no implicit active session in `session current/list` style output.

### 2. Validation now applies to library callers too
- Input validation is enforced inside `run_action(...)`, not only in CLI `__main__`.
- This closes the bypass path for direct module-level callers.

### 3. Reduced false positives in parameter validation
- Kept strict validation for path/session-like fields (`model`, `target`, `subsystem`, `session`).
- Stopped over-restricting `inspect --param` to avoid accidental rejection of valid parameter identifiers.

### 4. Test coverage expanded
- Added session-current strictness test for multi-session scenarios.
- Added tests verifying `run_action` validation enforcement.
- Added test ensuring `inspect --param` is not over-restricted.

## Commits
- `d921a42` fix(core): tighten strict session semantics and validation coverage

## Verification
Executed with direct `python.exe` path (to avoid pyenv shim/CMD UNC issues):

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Result:
- Ran 27 tests
- OK

## Notes
- In this environment, calling `python` through pyenv shim may fail under `\\?\...` path because shim invokes `cmd` with UNC path limitations.
- Using direct `python.exe` path is reliable for test execution.
