# CLI Contract Repair Design

Date: 2026-03-19
Scope: unified `simulink_cli` runtime, tests, shipped docs, plugin metadata, and maintainer docs

## Background

The repository is in generally good shape, but a focused audit found a small number of contract and documentation gaps:

1. `find` and `scan` do not consistently return stable contract errors when no model is opened and `bdroot()` cannot resolve an active model.
2. `find` does not use the same `find_system` search options as `scan`, which can produce inconsistent model visibility.
3. `set_param` validates `value` with the same reserved-character rules used for identifiers, which is too restrictive for legitimate MATLAB string values such as format strings containing `%`.
4. `session` action metadata and user-facing docs have drifted from the real runtime surface.
5. Maintainer docs and plugin metadata still contain stale pre-`simulink-edit` wording.
6. A few low-risk cleanup items remain, notably redundant casting in `connections.py` and silent local-state corruption fallback in `session.py`.

The repair should align runtime behavior, tests, docs, and metadata in a single pass without widening scope into unrelated refactoring.

## Goals

- Restore stable error-contract behavior for no-model resolution paths.
- Make `find` and `scan` use consistent search semantics.
- Relax `set_param.value` validation enough to allow real parameter payloads such as strings containing `%`, while preserving defensive validation for identifiers and unsafe input.
- Update tests so the repaired behavior is enforced by contract.
- Synchronize shipped docs, maintainer docs, and plugin metadata with the current product state.
- Clean up a small set of low-risk implementation annoyances discovered during review.

## Non-Goals

- No broad refactor of `inspect_block.py` or other large modules.
- No plugin version bump in this change.
- No new actions, no schema shape redesign, and no backward-compatibility wrapper work.
- No speculative validation relaxations beyond the confirmed `set_param.value` issue.

## Design

### 1. Stable model-resolution errors

`resolve_scan_root_path()` currently falls back to `eng.bdroot()` when no explicit model is provided and no opened models are found. That fallback can raise, which creates two bad outcomes:

- `find` may let the exception escape before action-level error handling.
- `scan` may degrade the situation into a generic `runtime_error`.

The helper should instead treat "cannot resolve an active model" as a stable domain error and return a structured error payload, not raise. The contract after repair is:

- `resolve_scan_root_path()` continues to return either:
  - a success dict: `{"model": ..., "scan_root": ...}`
  - or an error dict produced by `make_error(...)`
- When `bdroot()` fails during the "no explicit model + no opened models" fallback, the helper returns:
  - `error = "model_not_found"`
  - actionable `details` including the explicit model input and the currently opened model list
- `scan` and `find` must both consume that helper result the same way:
  - if `"error" in resolved`, return it directly
  - otherwise continue normal action execution

This keeps the interface boundary single and explicit. The repair should preserve the current `model_required` behavior when multiple opened models exist and no explicit model is given.

### 2. Consistent `find_system` visibility

`scan` already uses the following search-option prefix before action-specific arguments:

- `FollowLinks = on`
- `LookUnderMasks = all`

`find` should use the same visibility defaults so users and agents do not observe different model visibility depending on which action is used first. The required `find` construction after repair is:

- shared option prefix copied from `scan`:
  - `scan_root`
  - `"FollowLinks", "on"`
  - `"LookUnderMasks", "all"`
- followed by existing query-specific predicates already used by `find`:
  - `"RegExp", "on"` + `"Name", ...` when `name` is provided
  - `"BlockType", ...` when `block_type` is provided

No additional `scan`-specific arguments are implied by this change. In particular, `find` does not gain `SearchDepth` logic or recursive/shallow mode flags; the alignment is intentionally limited to visibility-related `find_system` options.

### 3. Field-specific validation for `set_param.value`

The current shared text validation rejects `%`, `?`, and `#` for all string fields. That rule is appropriate for identifier-like fields such as `target`, `param`, `model`, `subsystem`, and `session`, but not for arbitrary write payloads.

The design is:

- Keep existing strict validation for identifier-like fields.
- Introduce a dedicated validation path for `set_param.value`.
- `value` continues to reject:
  - empty string
  - leading/trailing whitespace
  - control characters
  - overlength input
- `value` no longer rejects `%` solely because it is a reserved identifier character.

This keeps the safety model intact while removing a false restriction on realistic parameter values.

### 4. Session action contract completion

`session list`, `session current`, and `session use` can all surface `engine_unavailable`, so the action metadata should declare it in `session_cmd.ERRORS`. This aligns action-level metadata with actual runtime behavior and top-level schema output.

### 5. Low-risk cleanup

Two opportunistic cleanup items are included because they are isolated and contract-safe:

- Remove redundant `int()` casts around already-validated `depth` in `connections.py`.
- When local session state cannot be parsed, continue the current non-fatal fallback to `{}`, but emit a concise stderr warning so corruption is diagnosable.

The warning must remain advisory only and must not block command execution.

## Implementation Order

The work should be planned and implemented in three bounded stages:

1. **Runtime contract fixes**
   - stable no-model error path
   - `find` visibility option alignment
   - `set_param.value` field-specific validation
   - `session_cmd.ERRORS` completion
   - tests that lock these behaviors
2. **Docs and metadata synchronization**
   - user-facing docs
   - maintainer docs
   - plugin and marketplace metadata
3. **Low-risk cleanup**
   - redundant `int()` cleanup
   - local-state corruption warning on stderr

Stages 2 and 3 are part of the same overall repair, but they are intentionally downstream of stage 1 so the plan stays anchored on contract repair rather than drifting into an open-ended cleanup sweep.

## Test Strategy

Update the test suite before or alongside implementation so each repaired behavior is enforced:

1. Add regression coverage for `scan` when no opened model exists and `bdroot()` fails:
   - expected error: `model_not_found`
2. Add regression coverage for `find` on the same path:
   - expected error: `model_not_found`
   - no framework-level exception escape
3. Extend `find` behavior tests to assert the action passes the same visibility options used by `scan`.
4. Add validation tests proving `set_param.value` accepts `%` but still rejects control characters and trim mismatch.
5. Add/extend tests covering `session` schema/action contract so `engine_unavailable` is declared for `session`.
6. Add state-file tests for corrupted local state:
   - state load falls back safely
   - stderr contains a warning

Existing contract tests should continue to pass unchanged unless they currently encode stale expectations.

## Documentation and Metadata Updates

### User-facing docs

Update these files to match repaired behavior and current product state:

- `README.md`
- `README.zh-CN.md`
- `skills/simulink_scan/SKILL.md`
- `skills/simulink_scan/reference.md`
- `skills/simulink_scan/test-scenarios.md`
- `skills/simulink_edit/SKILL.md`
- `skills/simulink_edit/reference.md`
- `skills/simulink_edit/test-scenarios.md`

Required updates:

- correct current plugin capability wording (`scan` + `edit`)
- include missing session-state error codes where user-facing docs enumerate common errors
- keep examples aligned with the unified `simulink_cli` entrypoint
- document that `set_param.value` is a string payload and may legitimately contain `%`

### Maintainer docs

Update these files:

- `.claude/CLAUDE.md`
- `.claude-plugin/PLUGIN_SCHEMA_NOTES.md`
- `docs/release/2026-03-07-github-marketplace-release-checklist.md`

Required updates:

- remove stale references to merged `test_edit_*` files
- add accurate unified test-map entries
- fix stale wording that still frames `simulink-edit` as future work
- correct stale release checklist assumptions now contradicted by the repository

### Plugin metadata

Update:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

Required updates:

- refresh descriptions so they describe the current suite accurately
- remove outdated future-facing keywords
- add `edit`-appropriate metadata where it materially improves discoverability
- keep version unchanged at `2.0.0`

## Verification

Minimum verification before claiming completion:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
python -m simulink_cli schema
python -m simulink_cli session list
```

`session list` is expected to return a stable session-related error in environments without MATLAB Engine, not crash.

## Risks and Mitigations

- Risk: relaxing `set_param.value` too broadly weakens input hardening.
  Mitigation: introduce field-specific validation rather than weakening shared identifier validation.

- Risk: changing model-resolution logic alters current fallback behavior.
  Mitigation: preserve existing success paths and only normalize the failure path into a stable domain error.

- Risk: doc sweep becomes noisy and misses one surface.
  Mitigation: update user docs, maintainer docs, and metadata in the same change and rely on contract tests plus manual grep verification.

## Implementation Shape

The repair should stay small and local:

- `simulink_cli/model_helpers.py`
- `simulink_cli/actions/find.py`
- `simulink_cli/actions/scan.py`
- `simulink_cli/actions/set_param.py`
- `simulink_cli/actions/session_cmd.py`
- `simulink_cli/actions/connections.py`
- `simulink_cli/session.py`
- targeted tests
- targeted docs and manifests

No additional modules are required.
