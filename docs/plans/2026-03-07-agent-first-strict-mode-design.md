# Agent-First Strict Mode Design (Phase 1)

Date: 2026-03-07
Status: Approved
Scope: Simulink scan CLI and skill behavior hardening for AI-agent usage

## Background

Current CLI behavior is partly optimized for convenience (for example, fuzzy session matching and implicit fallback). For AI-agent usage, this increases non-deterministic behavior and risk of wrong-target operations.

Phase 1 focuses on strict, fail-fast behavior with stable machine errors, while deferring JSON input mode to Phase 2.

## Decisions

1. Default behavior becomes strict.
2. Invalid input must return machine-readable errors and exit non-zero.
3. Fuzzy session matching is removed (code deletion, no compatibility mode).
4. Breaking behavior changes are accepted in development stage versioning (keep dev/alpha style under 1.0.0 track).
5. `--json` input is deferred to Phase 2.

## Phase 1 Scope

### In Scope

- Session resolution strictness:
  - Remove fuzzy/prefix/contains/close matching for session name resolution.
  - If multiple sessions exist and `--session` is not provided, return `session_required`.
  - If `--session` is provided but not exact match, return `session_not_found`.
- Unified argument validation for agent-facing fields:
  - `--model`
  - `--target`
  - `--subsystem`
  - `--session`
- Input hardening rules:
  - Reject ASCII control characters.
  - Reject `?`, `#`, `%`.
  - Reject leading/trailing whitespace differences.
  - Reject over-length values (exact limit to be finalized in implementation plan).
- Documentation alignment:
  - Update README and skill docs to reflect strict default and fuzzy removal.

### Out of Scope (Phase 2+)

- JSON request input mode (`--json`).
- Runtime schema introspection command (`schema`/`describe`).
- Output-size controls such as NDJSON and structured field-selection knobs.

## Error Contract

All errors should be normalized to:

```json
{
  "error": "<stable_code>",
  "message": "<human_readable>",
  "details": {}
}
```

### Minimum Error Codes for Phase 1

- `invalid_input`
- `session_required`
- `session_not_found`
- `model_required` (existing behavior remains)
- `unknown_parameter` (existing behavior remains)
- `inactive_parameter` (existing behavior remains)

## Execution Flow Changes

1. Parse args.
2. Run centralized input validation by action/field.
3. On validation failure: emit normalized error JSON and exit 1.
4. On success: execute action logic.
5. For session resolution:
   - zero sessions: existing no-session error path.
   - one session: allow implicit use.
   - multiple sessions:
     - no `--session`: `session_required`
     - provided `--session` and not exact: `session_not_found`

## Testing Plan (Phase 1)

### New Tests

- Session strictness tests:
  - multi-session + missing `--session` -> `session_required`
  - multi-session + non-exact `--session` -> `session_not_found`
  - verify fuzzy/prefix/contains/close no longer resolves
- Input validation tests:
  - control chars
  - `?/#/%`
  - leading/trailing whitespace
  - over-length
  - all return `invalid_input`

### Regression Guard

- Existing unit tests stay green.

## Acceptance Criteria

- CLI enforces strict session selection deterministically.
- Illegal agent-like inputs are rejected before action execution.
- Error payloads are machine-stable.
- README and SKILL docs match behavior.
- Unit tests pass with new coverage for strictness and hardening.

