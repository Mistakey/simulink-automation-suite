# Single-Parameter Agent Loop Design

Date: 2026-03-20
Scope: `simulink_cli` contract surface, `set_param` write semantics, read/write workflow boundaries, tests, and shipped docs

## Background

The repository already has the right primitive action surface for a small Simulink edit loop:

- read-only discovery and analysis via `scan`, `find`, `inspect`, and `connections`
- a single write action via `set_param`
- rollback-aware write responses
- dry-run preview support
- cross-skill workflow tests

That is enough to support a meaningful agent workflow, but not enough to claim a complete small-task autonomous loop.

The current gap is not "missing more write commands." The current gap is that the loop is still action-level reliable rather than workflow-level reliable:

1. `dry_run` preview and execute are still two loosely related calls.
2. The runtime does not enforce that execute is still acting on the same observed precondition as preview.
3. Recovery behavior is partly documented in runbooks rather than fully expressed in machine-facing contract fields.
4. Error semantics around write verification are not fully aligned across runtime behavior, docs, and recovery guidance.
5. Current tests strongly prove functional correctness, but they do not yet fully prove agent-safe autonomous execution under stale previews, changed target state, and structured recovery paths.

The next version should therefore optimize for agent autonomy on a deliberately narrow task shape instead of expanding capability breadth.

## Version Goal

Turn Simulink Automation Suite into a tool that can reliably support this narrow autonomous task:

"Locate one target block, modify one parameter, verify the result, and recover safely if the preview is stale or the write fails."

This version is successful when an AI agent can more safely complete that loop without depending on extra human judgement between preview, execute, verification, and recovery.

## Product Boundary

This version explicitly targets:

- single target block
- single parameter
- single intended value
- one preview
- one guarded execute
- one verification step
- one explicit recovery path when needed

This version explicitly does not target:

- multi-parameter transactions
- structural edits such as add/delete block or line
- batch operations
- hidden task memory or long-lived job context
- automatic rollback
- broader human-oriented CLI ergonomics

This boundary is intentionally narrow. The repository already has enough primitives for this task shape, and a narrower scope keeps the contract explicit, testable, and agent-safe.

## Goals

- Preserve the current action set and single-write-command model.
- Make preview output directly usable as the input for a guarded execute step.
- Prevent execute from writing when the previewed precondition is no longer true.
- Normalize write failure semantics so agents can recover deterministically.
- Keep the workflow explicit and stateless from the caller's perspective.
- Define a small, testable autonomous loop around existing read-only actions plus `set_param`.

## Non-Goals

- No second write action.
- No server-side preview cache or preview token store.
- No expansion of `find`, `scan`, or `connections` into higher-level write planning tools.
- No attempt to solve general-purpose Simulink editing workflows in this version.
- No attempt to make the tool autonomously choose the engineering intent of a parameter change.

## Design Summary

### 1. Keep one write action, but make execute guarded

`set_param` remains the only write action.

The version change is semantic, not capability-count-based:

- `dry_run=true` remains the preview mode
- `dry_run=false` becomes a guarded execute mode with explicit preconditions

The core design is compare-and-swap style execution:

1. preview reads the current value
2. preview returns a machine-executable `apply_payload`
3. execute re-reads current state before writing
4. execute writes only if the expected precondition still holds
5. execute otherwise fails safely without mutation

This preserves the repo's explicit JSON-first design and avoids hidden state.

### 2. Preview must return an executable apply payload

Current preview output already returns descriptive diff information plus rollback. The next version extends preview so it also returns a direct execution payload.

Recommended response additions for preview:

```json
{
  "action": "set_param",
  "dry_run": true,
  "target": "my_model/Gain1",
  "param": "Gain",
  "current_value": "1.5",
  "proposed_value": "2.0",
  "apply_payload": {
    "action": "set_param",
    "target": "my_model/Gain1",
    "param": "Gain",
    "value": "2.0",
    "dry_run": false,
    "expected_current_value": "1.5"
  },
  "rollback": {
    "action": "set_param",
    "target": "my_model/Gain1",
    "param": "Gain",
    "value": "1.5",
    "dry_run": false
  }
}
```

### Session propagation rule

`session` remains an optional first-class `set_param` request field. This version does not introduce any new session field beyond the existing action contract.

The propagation rule should be explicit:

- if the caller explicitly supplied `session` in the original request, preview must preserve the same `session` field in both `apply_payload` and `rollback`
- if the caller did not supply `session`, preview must omit `session` from both payloads
- runtime must not inject a hidden inferred session into `apply_payload` or `rollback`

This keeps session affinity explicit and prevents accidental coupling between a saved active session and a replayed write payload.

Examples:

- explicit-session flow:
  request contains `"session":"MATLAB_12345"` -> preview returns the same `"session":"MATLAB_12345"` inside both `apply_payload` and `rollback`
- implicit-session flow:
  request omits `session` -> preview also omits `session` from both payloads, even if the runtime resolved the active session through existing selection rules

`apply_payload` is not advisory text. It is the intended machine contract for the next step.

### 3. Execute must enforce explicit preconditions

When `dry_run=false`, `set_param` should:

1. validate target block exists
2. validate parameter exists
3. read the current value before writing
4. if `expected_current_value` is present, compare it against the currently observed value
5. reject execution when the value no longer matches
6. otherwise perform the write
7. read back and verify the result

This gives the caller a safe way to distinguish:

- "my preview is still valid"
- "my preview is stale, so I must re-read before writing"
- "the write itself failed"
- "the write may have happened, but verification did not confirm it"

### 4. Prefer stateless guarded execution over preview tokens

This design explicitly rejects a server-side preview token model.

Reasons:

- hidden preview state would weaken the current explicit contract style
- token lifetime and invalidation would create unnecessary coordination complexity
- task memory is easy to get wrong in multi-session or mixed user/agent workflows
- the repository currently favors schema-first explicit payloads over implicit workflow memory

The recommended design is therefore stateless guarded execution using `expected_current_value`, not stateful token lookup.

## Read/Write Workflow Boundary

This version should not broaden read-only actions into speculative planning tools.

The workflow boundary should become clearer:

- `find`
  - identifies candidate blocks
  - returns stable target paths for downstream use
- `inspect`
  - becomes the standard read step before preview, after execute, and during recovery
  - is the canonical way to confirm the current value of a parameter
- `scan`
  - remains architecture/topology context
  - does not become part of guarded write semantics
- `connections`
  - remains signal/context analysis
  - does not become part of guarded write semantics
- `set_param`
  - owns preview, guarded execute, verification, and rollback payload generation

The intended small-task loop is:

1. `find` or `scan` to locate the target
2. `inspect` to confirm the current parameter state
3. `set_param` with `dry_run=true`
4. replay returned `apply_payload`
5. `inspect` again to verify or diagnose
6. replay `rollback` if required

This keeps the minimum loop explicit and agent-friendly:

- `find` answers "what object should I consider?"
- `inspect` answers "what is the current parameter state?"
- `set_param` answers "what would I change / can I still change it safely / did it work?"

## Error Contract

The next version should make write failure modes explicit and non-overlapping.

### Existing validation and targeting errors remain part of the loop

The guarded-write release does not replace the current base contract. These existing errors still matter and should remain explicitly planned:

- `invalid_json`
- `json_conflict`
- `unknown_parameter`
- `invalid_input`
- `session_required`
- `session_not_found`
- `no_session`
- `engine_unavailable`
- `block_not_found`
- `param_not_found`

Their semantics in this version should be:

| Error | Meaning in guarded loop | Mutation expected | `safe_to_retry` | `recommended_recovery` |
|---|---|---:|---:|---|
| `invalid_json` | request shape or type is invalid | no | true | `rerun_dry_run` |
| `json_conflict` | JSON mode mixed with flags | no | true | `rerun_dry_run` |
| `unknown_parameter` | unsupported request field | no | true | `rerun_dry_run` |
| `invalid_input` | required field missing or invalid | no | true | `rerun_dry_run` |
| `session_required` | multiple sessions exist and the caller did not disambiguate | no | true | `inspect_then_retry` |
| `session_not_found` | explicit session is invalid | no | true | `inspect_then_retry` |
| `no_session` | no MATLAB shared session is available at all | no | true | `inspect_then_retry` |
| `engine_unavailable` | MATLAB engine unavailable | no | false | `inspect_then_retry` |
| `block_not_found` | target block cannot be resolved | no | true | `inspect_then_retry` |
| `param_not_found` | target block does not expose requested parameter | no | true | `inspect_then_retry` |

The important planning distinction is:

- these errors are pre-write failures
- they do not participate in stale-preview detection
- they must remain machine-distinguishable from post-attempt write failures

For invalid or unsupported values, the split should stay explicit:

- malformed request payloads remain `invalid_json` or `invalid_input`
- values that are syntactically valid but rejected by MATLAB during the write remain `set_param_failed`

### New or clarified write errors

- `precondition_failed`
  - meaning: the requested write was not attempted because the previewed state is stale
  - expected effect: no mutation should have occurred
  - expected recovery: inspect or rerun dry-run before retrying

- `set_param_failed`
  - meaning: the write call itself failed before verified success
  - expected effect: mutation may or may not have occurred depending on `write_state`
  - expected recovery: follow structured recovery hints

- `verification_failed`
  - meaning: the write call ran, but read-back did not confirm success
  - expected effect: mutation may already have happened
  - expected recovery: inspect or rollback

This spec intentionally recommends making `verification_failed` a real top-level error code instead of only a `write_state` detail. The current split between docs and runtime behavior should be removed.

### Recovery metadata

For machine-facing recovery, write errors should include structured hints in `details`:

- `write_state`
- `safe_to_retry`
- `recommended_recovery`

Recommended `recommended_recovery` values:

- `rerun_dry_run`
- `inspect_then_retry`
- `rollback`

Suggested interpretation:

| Error | Expected mutation state | `safe_to_retry` | `recommended_recovery` |
|---|---|---:|---|
| `precondition_failed` | not written | true | `rerun_dry_run` |
| `set_param_failed` before write | not written | true | `inspect_then_retry` |
| `set_param_failed` after attempted write | unknown | false | `inspect_then_retry` or `rollback` |
| `verification_failed` | unknown / possibly written | false | `rollback` or `inspect_then_retry` |

The existing human-readable `suggested_fix` field should remain, but it should no longer be the only way an agent learns the next step.

## Response Shape Recommendations

### Preview success

Must include:

- `action`
- `dry_run`
- `target`
- `param`
- `current_value`
- `proposed_value`
- `apply_payload`
- `rollback`
- `write_state = "not_attempted"`

### Execute success

Must include:

- `action`
- `dry_run = false`
- `target`
- `param`
- `previous_value`
- `new_value`
- `verified = true`
- `rollback`
- `write_state = "verified"`

### Precondition failure

Should return error envelope with:

- `error = "precondition_failed"`
- `details.expected_current_value`
- `details.observed_current_value`
- `details.safe_to_retry = true`
- `details.recommended_recovery = "rerun_dry_run"`
- no ambiguity that the write was not attempted

### Execute failure after write attempt

Should return error envelope with:

- the relevant top-level error code
- `details.write_state`
- `details.rollback`
- `details.safe_to_retry`
- `details.recommended_recovery`
- observed value when available

## Architecture Impact

The design should stay concentrated in the current write surface rather than spread across the whole codebase.

Primary impact areas:

- `simulink_cli/actions/set_param.py`
- `simulink_cli/core.py`
- schema and error-code contract tests
- workflow tests
- shipped docs for README, `simulink_edit`, and examples/recovery guidance

Read-only actions should only be touched where needed to align examples and workflow guidance. They are not the main locus of change.

## Test Strategy

This version needs to prove workflow-level safety, not just command presence.

### 1. Contract tests

Add or update tests to verify:

- schema includes `expected_current_value` when applicable to `set_param`
- schema includes `precondition_failed`
- preview response includes `apply_payload`
- preview and execute response shapes remain stable
- docs, README, and skill/reference files describe the same write failure semantics as runtime

### 2. Workflow tests

Add or update tests to verify:

- `inspect -> dry_run -> apply_payload -> inspect` success path
- stale preview causes `precondition_failed`
- execute failure returns structured recovery hints
- verification failure returns the correct top-level error semantics
- rollback replay still works after the guarded execution change

### 3. Live MATLAB smoke verification

This version should not be considered complete without explicit live smoke coverage for the guarded loop:

- preview one real parameter change
- execute from returned `apply_payload`
- verify result with `inspect`
- simulate stale preview and confirm guarded refusal
- replay rollback and verify original value restored

The purpose of live smoke here is not generic MATLAB compatibility. It is specifically to prove that the autonomous loop contract works under real runtime behavior.

## Acceptance Criteria

This version is complete only when all of the following are true:

- an agent can take preview output and directly execute the returned `apply_payload`
- execute rejects stale previews without mutating the model
- `precondition_failed`, `set_param_failed`, and `verification_failed` are machine-distinguishable
- every write failure path returns enough structured recovery information for an agent to choose a next step without relying only on prose
- docs and runtime no longer disagree about verification-failure semantics
- the standard small-task loop is clearly documented as `find/inspect -> set_param dry_run -> apply_payload -> inspect -> rollback if needed`

## Risks and Mitigations

- Risk: the contract grows too clever and becomes hard for agents to follow.
  Mitigation: keep one write action, one guarded execute path, one explicit `apply_payload`, and no hidden state.

- Risk: adding precondition checks makes the tool feel stricter.
  Mitigation: that strictness is the product improvement; stale preview refusal is safer than silent mutation.

- Risk: recovery metadata duplicates `suggested_fix`.
  Mitigation: keep prose for humans and structured fields for agents; both serve different callers.

- Risk: this version is mistaken for a general transaction system.
  Mitigation: keep the scope fixed to one target, one parameter, one value, one guarded execute.

## Release Positioning

The next version should be described as a reliability and workflow-contract release, not a capability-expansion release.

Recommended positioning sentence:

"This release strengthens the agent-safe single-parameter edit loop by turning preview output into a guarded execution contract with explicit recovery semantics."
