# MATLAB Session Error Recovery Design

Date: 2026-03-07
Topic: Distinguish `engine_unavailable` vs `no_session` and align docs for agent recovery
Status: Approved

## Context

Current behavior conflates two failure modes in MATLAB session bootstrap:

1. MATLAB Engine for Python is unavailable in current Python environment.
2. MATLAB Engine is available, but no shared MATLAB session exists because `matlab.engine.shareEngine` has not been run.

As a result, agents may receive non-deterministic error text and provide incorrect next-step guidance.

## Goals

- Add stable machine error code `engine_unavailable`.
- Keep `no_session` for missing shared MATLAB session.
- Ensure AI receives deterministic JSON contract and correct recovery instructions.
- Update docs (README + skill references) with prerequisites and recovery guidance.

## Non-Goals

- No major exception-class refactor across the whole runtime.
- No behavior change to scan/inspect payload schema beyond error-path clarity.

## Considered Approaches

### A. Text-pattern mapping in `map_runtime_error`

Pros: Smallest code delta.
Cons: Fragile to message wording changes; poor maintainability.

### B. Source-level stable error emission (Recommended)

Pros: Clear semantics at origin, stable tests, maintainable contract.
Cons: Moderate edits across session layer, mapper, tests, docs.

### C. Full typed exception hierarchy

Pros: Most structured.
Cons: High refactor cost for current scope.

Decision: **Approach B**.

## Design

### 1) Session layer (`sl_session.py`)

- `_get_matlab_engine()` should raise `RuntimeError("engine_unavailable")` when `matlab.engine` cannot be imported.
- `discover_sessions()` should preserve this stable code path.
- `resolve_target_session()` keeps existing behavior:
  - empty sessions -> `RuntimeError("no_session")` + stderr actionable guide
  - explicit mismatch -> `RuntimeError("session_not_found")`
  - multiple sessions without explicit selection -> `RuntimeError("session_required")`
- Other unknown failures remain generic runtime failures.

### 2) Error mapper (`sl_core.py`)

- Add `engine_unavailable` to `_ERROR_CODES` contract.
- Extend `map_runtime_error()` mapping table with deterministic message and suggested_fix:
  - `engine_unavailable`: install/configure MATLAB Engine for Python in active interpreter.
- Keep existing mappings for `no_session`, `session_required`, `session_not_found` unchanged.

### 3) Tests

- Extend runtime mapping test to include `engine_unavailable`.
- Add/extend session tests to verify import-failure path emits stable `engine_unavailable` behavior.
- Preserve current `no_session` tests to prevent regressions.

### 4) Documentation

Update the following documents:

- `README.md`
- `README.zh-CN.md`
- `skills/simulink_scan/SKILL.md`
- `skills/simulink_scan/reference.md`

Required additions:

- Prerequisites include MATLAB Engine for Python installation and environment alignment.
- Shared-session prerequisite include running `matlab.engine.shareEngine` in MATLAB.
- Recovery routing includes new `engine_unavailable` path distinct from `no_session`.

## Data Flow (Error Path)

1. Request enters `sl_core.main()`.
2. `run_action()` calls `connect_to_session()` for MATLAB-bound actions.
3. Session resolution attempts engine import and session discovery.
4. Stable error code emitted from source (`engine_unavailable` or `no_session` etc.).
5. `map_runtime_error()` converts to machine JSON with `error/message/details/suggested_fix`.

## Acceptance Criteria

- `engine_unavailable` appears in schema/error contract and mapper output.
- `no_session` remains unchanged for missing shared MATLAB session.
- README and skill docs explicitly document both prerequisites.
- Test suite remains green:
  - `python -m unittest discover -s tests -p "test_*.py" -v`

## Risks and Mitigations

- Risk: Over-catching exceptions could hide diagnostics.
  - Mitigation: Only canonicalize known paths; retain detailed `runtime_error` fallback.
- Risk: Doc drift across EN/ZH and skill reference.
  - Mitigation: Update both readmes and both skill docs in same change set.

## Implementation Handoff

Next step: use `writing-plans` workflow to produce a concrete step-by-step implementation plan before code edits.
