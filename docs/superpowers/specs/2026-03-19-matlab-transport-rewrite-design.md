# MATLAB Transport Rewrite Design

Date: 2026-03-19
Scope: unified `simulink_cli` runtime, MATLAB Engine integration layer, tests, and shipped docs

## Background

Real end-to-end testing against MATLAB R2024b and a live Simulink model surfaced a mismatch between the repository's mocked confidence and real runtime behavior:

1. `set_param` with `dry_run=false` can modify the model while the Python side still fails with a MATLAB Engine "Too many output arguments" error.
2. Write failure on that path prevents the caller from receiving the success payload and rollback contract expected by the current design.
3. Runtime/domain errors and protocol/request-shape errors are not consistently separated across actions.
4. Current shared text validation rejects control characters in block paths and subsystem paths, which blocks legitimate Simulink objects whose names contain such characters.
5. MATLAB warnings can leak outside the JSON contract and threaten machine-readable stdout.
6. Existing tests rely heavily on idealized fake engines and do not model key MATLAB Engine integration semantics such as `nargout=0`, warning leakage, or complex string/path transport.

These are not isolated action bugs. They all sit at the boundary where action modules directly call MATLAB Engine methods without a unified transport contract.

## Goals

- Make live MATLAB calls predictable and transport-safe across all actions.
- Repair `set_param` so real writes, rollback payloads, and verification work on live models.
- Separate protocol-layer errors from runtime/domain errors and document that split clearly.
- Support real Simulink paths containing control characters and other complex characters.
- Guarantee that stdout remains a single machine-readable JSON payload.
- Rebuild tests so they cover real MATLAB Engine semantics closely enough to catch transport bugs before release.
- Keep the action surface (`schema`, `session`, `list_opened`, `scan`, `find`, `inspect`, `connections`, `highlight`, `set_param`) intact.

## Non-Goals

- No new actions or plugin capabilities.
- No expansion into block creation/deletion, line editing, model save flows, or batch write APIs.
- No broad rewrite of action business logic beyond what is needed to move MATLAB call semantics into the transport layer.
- No speculative schema redesign unrelated to the verified runtime issues.

## Design

### 1. Introduce a unified MATLAB transport layer

Add a new module: `simulink_cli/matlab_transport.py`.

This module becomes the only place that knows how Python talks to MATLAB Engine. Action modules stop calling `eng.find_system`, `eng.get_param`, `eng.set_param`, and similar methods directly.
The only intended raw-engine exceptions after the rewrite are `session.py` for session connection/discovery and `matlab_transport.py` for actual MATLAB invocation.

The transport layer should expose a small, explicit API:

- `call(name, *args, nargout=1)` for regular MATLAB function calls with return values
- `call_no_output(name, *args)` for side-effecting MATLAB calls that must run with `nargout=0`
- `get_param(target, param)`
- `set_param(target, param, value)`
- `find_system(*args)`
- `hilite_system(target)`

The transport layer owns:

- explicit `nargout` handling
- safe string/path/value transport into MATLAB
- warning capture and normalization
- conversion of raw MATLAB exceptions into transport exceptions or structured failure data

This is a targeted architectural rewrite, not a framework. The layer exists to concentrate known integration risk into one boundary.

### 2. Move all MATLAB call semantics behind transport

Action modules remain responsible for:

- validating request arguments
- choosing the business flow
- mapping transport failures into plugin error codes
- shaping final JSON responses

Action modules stop being responsible for:

- deciding whether a MATLAB call needs `nargout=0`
- hand-rolling direct engine calls
- coping individually with warning leakage
- inventing ad hoc string escaping for paths or payloads

The intended request flow after the rewrite is:

`CLI/JSON request -> core.py -> action.validate -> action.execute -> matlab_transport -> MATLAB Engine -> normalized transport result -> action JSON payload -> stdout`

### 3. Fix `set_param` at the transport boundary

`set_param` is the immediate blocker and drives the transport design.

The rewritten `set_param` path should:

1. read and store the current parameter value
2. build the rollback payload before attempting the write
3. execute the write through a transport method that guarantees `nargout=0`
4. re-read the parameter value for verification
5. return a success payload when verification completes
6. return a structured failure payload when write or verification fails, including rollback information whenever a write may already have been attempted

The preferred primary implementation is a direct MATLAB Engine call with explicit `nargout=0`, not a string-built `eval` path. A string-eval fallback may exist only if a specific engine API corner case demands it.

Success response remains conceptually the same:

- `action`
- `dry_run`
- `target`
- `param`
- `previous_value`
- `new_value`
- `verified`
- `rollback`

Failure handling becomes stronger:

- `set_param_failed` remains the top-level error code for write-path failures
- automatic rollback must **not** happen inside the CLI
- when execute mode has already read the pre-write value, every execute-path error must include `details.rollback`
- `details` should include enough state to recover safely:
  - attempted target/param/value
  - MATLAB cause text
  - post-write observed value when available
  - rollback payload
  - a write-state indicator

Recommended write-state field values:

- `not_attempted`
- `attempted`
- `verified`
- `verification_failed`
- `unknown`

This makes "model may already be modified" explicit instead of silently stranding the caller.

The contract for each execution path should be explicit:

| Case | Top-level shape | `verified` | `write_state` | `rollback` placement | Notes |
|---|---|---|---|---|---|
| Dry-run success | success payload | omitted | `not_attempted` | top-level `rollback` | no write attempted |
| Execute success | success payload | `true` | `verified` | top-level `rollback` | write succeeded and read-back matched |
| Execute failure before mutation | error envelope | omitted | `not_attempted` | `details.rollback` | safe to retry; rollback still included for contract consistency |
| Execute failure after mutation attempt but before verification | error envelope | omitted | `attempted` or `unknown` | `details.rollback` | caller must assume model may have changed |
| Execute verification failure | error envelope | omitted | `verification_failed` | `details.rollback` | read-back did not prove requested value; caller must inspect or rollback |

There is no success case with `verified=false`. If verification does not succeed, the action returns `set_param_failed`.

### 4. Separate protocol errors from runtime/domain errors

The current contract should be tightened into two categories:

#### Protocol/request-shape errors

These remain parser/framework errors and keep using:

- `invalid_json`
- `json_conflict`
- `unknown_parameter`
- `invalid_input`

`unknown_parameter` must only mean "the caller supplied a field or flag that is not part of the contract."

#### Runtime/domain errors

These describe the Simulink/MATLAB target state:

- `model_not_found`
- `model_required`
- `subsystem_not_found`
- `invalid_subsystem_type`
- `block_not_found`
- `param_not_found`
- `inactive_parameter`
- `session_required`
- `session_not_found`
- `no_session`
- `engine_unavailable`
- `set_param_failed`
- `runtime_error`

This implies one intentional contract change:

- `inspect` single-parameter lookup should return `param_not_found` when the target block does not expose the requested parameter.
- `unknown_parameter` should no longer be used for that condition.

That change aligns runtime behavior with user intuition and with the recovery flow documented for edit/read operations.

### 5. Support complex block and subsystem paths

Current shared validation treats control characters as universally invalid. That is too strict for Simulink paths and subsystem names.

The rewrite should split validation by field semantics:

The validation matrix must be explicit:

| Field | Semantic class | JSON mode | Flag mode | Notes |
|---|---|---|---|---|
| `session` | session identifier | strict: reject control chars and reserved identifier punctuation | same as JSON | exact shared-engine name; not a MATLAB object path |
| `model` | MATLAB object name | allow arbitrary string except empty/NUL/overlength | support simple shell-safe strings; complex names best-effort only | recommend JSON for control chars or multiline names |
| `target` | MATLAB object path | allow arbitrary string except empty/NUL/overlength | support simple shell-safe strings; complex paths best-effort only | primary path field; must support embedded newlines in JSON |
| `subsystem` | MATLAB object path fragment | allow arbitrary string except empty/NUL/overlength | support simple shell-safe strings; complex paths best-effort only | same transport rules as `target` |
| `param` | MATLAB-facing parameter name | allow arbitrary string except empty/NUL/overlength | support simple shell-safe strings; complex names best-effort only | no reserved-punctuation denial at validation layer |
| `value` | write payload | allow arbitrary string except empty/NUL/overlength | support simple shell-safe strings; complex values best-effort only | supports `%`, embedded newlines, and other payload characters |

Two contract rules follow from this matrix:

- reserved-character denial remains only for parser/framework identifiers such as `session`, not for MATLAB-facing object names or payload strings
- JSON mode is the canonical contract surface for complex names, paths, and values; flag mode is guaranteed only for ordinary shell-safe strings

The transport layer must pass these values to MATLAB without expression injection or broken quoting.

### 6. Guarantee clean JSON stdout

The CLI contract depends on stdout being a single JSON payload.

The transport layer must prevent MATLAB warnings from corrupting stdout. The design requirement is:

- warning text must never appear before or after the JSON payload on stdout

The warning contract should be concrete:

- all MATLAB-originated warnings are captured by transport, never printed directly to stdout
- successful action responses may include optional top-level `warnings: string[]`
- error responses keep the fixed error-envelope shape, so warnings go in `details.warnings`
- transport does not emit MATLAB warnings to stderr as a normal action path
- stderr remains reserved for local maintainer-facing infrastructure diagnostics outside the action payload contract

Warnings are surfaced when they change how a caller should interpret the response. Pure noise warnings may be dropped by transport, but that policy must be action-agnostic and deterministic enough to test.

### 7. Normalize transport-facing action behavior

After the rewrite, action responsibilities should look like this:

- `set_param`: uses transport for read/write/verify and maps write-state failures cleanly
- `inspect`: uses transport for parameter access and returns `param_not_found` for missing runtime parameters
- `scan`, `find`, `connections`: use transport wrappers for `find_system` and related parameter reads so warning behavior and path transport are consistent
- `highlight`: uses a transport wrapper for visual-only highlighting
- `list_opened` and helper paths must use transport-backed calls whenever they touch MATLAB state

No action should need to know whether the underlying MATLAB call was a direct engine method, a function wrapper, or a no-output command.

## Implementation Shape

Expected primary touch points:

- `simulink_cli/matlab_transport.py` (new)
- `simulink_cli/validation.py`
- `simulink_cli/actions/set_param.py`
- `simulink_cli/actions/inspect_block.py`
- `simulink_cli/actions/scan.py`
- `simulink_cli/actions/find.py`
- `simulink_cli/actions/connections.py`
- `simulink_cli/actions/highlight.py`
- `simulink_cli/model_helpers.py`
- targeted tests and docs

`session.py` should remain focused on session discovery and connection, not absorb transport logic.

After the rewrite, no module other than `session.py` and `matlab_transport.py` should make raw MATLAB Engine calls. `model_helpers.py` is therefore a required migration target, not optional.

## Test Strategy

The current suite should be expanded in three layers.

### 1. Transport unit tests

Add focused tests for the new transport module, including:

- side-effecting calls must use `nargout=0`
- direct no-output call failure surfaces the original cause cleanly
- warning capture does not pollute stdout
- complex string/path arguments survive transport unchanged
- value/target pairs used by `set_param` can include control characters and percent-format strings

These tests need richer engine doubles than the current simple fakes. The doubles must model MATLAB Engine semantics that matter here, especially "fails when a no-output function is called without `nargout=0`."

### 2. Action regression tests

Update and extend action tests to verify:

- `set_param` execute path uses transport and returns rollback on successful live-write simulation
- `set_param` failure after attempted write exposes rollback and write-state details
- `inspect` missing single parameter returns `param_not_found`
- complex `target` and `subsystem` values are accepted by validation and routed intact
- `model_helpers.py` and model-resolution helpers do not bypass transport
- warning-bearing `scan`/`find` flows still produce clean structured responses

### 3. CLI contract tests

Add or tighten tests for:

- kebab-case output-control flags:
  - `--max-blocks`
  - `--max-params`
  - `--max-edges`
  - `--max-results`
- boolean flag behavior:
  - `--dry-run`
  - `--no-dry-run`
- JSON-mode recommendation for complex path/value payloads
- warning placement:
  - top-level `warnings` on success
  - `details.warnings` on error
- stdout containing only valid JSON even when MATLAB emits warnings

### 4. Optional live smoke tests

The repository should define an opt-in local verification path for maintainers with MATLAB available. These are not required for default CI, but they are required before claiming the transport rewrite solved the live issues.

Minimum live smoke coverage:

- `set_param` dry-run
- `set_param` execute
- rollback execution
- newline-containing `target` or `value` coverage on a real model
- special-character path targeting
- `scan`/`find` on a warning-prone model without stdout corruption

## Documentation Updates

All shipped docs must reflect the repaired contract in one pass.

Update:

- `README.md`
- `README.zh-CN.md`
- `skills/simulink_scan/SKILL.md`
- `skills/simulink_scan/reference.md`
- `skills/simulink_scan/test-scenarios.md`
- `skills/simulink_edit/SKILL.md`
- `skills/simulink_edit/reference.md`
- `skills/simulink_edit/test-scenarios.md`
- `.claude/CLAUDE.md`

Required documentation changes:

- explain that JSON mode is the preferred path for complex strings and special-character paths
- align `inspect` single-parameter missing-name behavior with `param_not_found`
- document clean stdout as a contract invariant
- document that write failures may include rollback and write-state details when the write may already have been attempted
- remove wording that implies current tests alone are sufficient proof of live MATLAB compatibility

## Implementation Order

The rewrite should be implemented in four bounded stages:

1. **Transport foundation**
   - add `matlab_transport.py`
   - define transport result/error shape
   - add transport tests
2. **Critical path migration**
   - migrate `set_param`
   - migrate `inspect`
   - align error semantics (`param_not_found` vs `unknown_parameter`)
3. **Read-surface migration**
   - migrate `scan`, `find`, `connections`, `highlight`
   - centralize warning handling
   - relax path validation where required
4. **Contract synchronization**
   - docs
   - scenario files
   - maintainer docs
   - final verification against live MATLAB

This ordering keeps the blocker and the contract semantics ahead of the broader cleanup work.

## Verification

Minimum non-live verification before claiming implementation complete:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m simulink_cli schema
```

Minimum live verification before claiming the rewrite solved the reported field issues:

```bash
python -m simulink_cli --json "{\"action\":\"set_param\",\"target\":\"<real target>\",\"param\":\"<real param>\",\"value\":\"<value>\"}"
python -m simulink_cli --json "{\"action\":\"set_param\",\"target\":\"<real target>\",\"param\":\"<real param>\",\"value\":\"<value>\",\"dry_run\":false}"
python -m simulink_cli --json '{"action":"set_param","target":"<real target>","param":"<real param>","value":"<rollback value>","dry_run":false}'
```

The live write verification must confirm all of the following:

- no "Too many output arguments" failure
- returned payload includes rollback
- verify/read-back confirms the write
- rollback succeeds
- stdout remains valid JSON

## Risks and Mitigations

- Risk: transport rewrite grows into broad business refactoring.
  Mitigation: keep action responsibilities intact and move only MATLAB call semantics plus warning/transport handling.

- Risk: path-validation relaxation weakens input hardening too much.
  Mitigation: split validation by field semantics instead of weakening all text validation globally.

- Risk: warning suppression hides useful MATLAB diagnostics.
  Mitigation: surface actionable warnings in structured response fields and only suppress transport noise from stdout.

- Risk: transport-layer tests still do not match real MATLAB behavior.
  Mitigation: add richer engine doubles and require opt-in live verification before declaring the rewrite complete.

## Open Design Constraint

Because the product requirement now explicitly includes support for names containing control characters, the transport layer must be treated as the contract boundary for safe value passing. If the final MATLAB Engine API shape cannot safely support a direct function call for a specific operation, the fallback strategy must still preserve:

- exact string fidelity
- no stdout corruption
- deterministic rollback recovery

That constraint takes priority over preserving the current validation model.
