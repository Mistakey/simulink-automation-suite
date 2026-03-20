# Single-Parameter Agent Loop Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `set_param` into a guarded single-parameter write loop that returns executable preview payloads, rejects stale previews without mutating, and gives agents structured recovery guidance.

**Architecture:** Keep the existing action surface intact. Implement the guarded loop entirely inside `simulink_cli/actions/set_param.py`, extend the current test fakes and workflow tests to prove the new contract, and then align README plus `simulink_edit` docs with the runtime semantics. Avoid hidden workflow state; use explicit request/response fields only.

**Tech Stack:** Python 3.10+, `unittest`, existing `simulink_cli` action modules, current fake MATLAB engines in `tests/fakes.py`, Claude plugin docs and contract tests.

---

## Spec Reference

- Spec: `docs/superpowers/specs/2026-03-20-single-parameter-agent-loop-design.md`

## File Structure

### Runtime and contract files

- Modify: `simulink_cli/actions/set_param.py`
  - Owns all guarded preview/execute semantics, request validation, failure taxonomy, recovery metadata, and `apply_payload` generation.
- Do not modify unless tests prove it is required: `simulink_cli/core.py`
  - Schema aggregation should update automatically from `FIELDS` and `ERRORS` on `set_param.py`.

### Test files

- Modify: `tests/test_schema_action.py`
  - Lock new `set_param` field metadata and new error codes into the schema contract.
- Modify: `tests/test_error_contract.py`
  - Lock `precondition_failed` and `verification_failed` into aggregated error-code expectations.
- Modify: `tests/test_json_input_mode.py`
  - Cover JSON parsing for `expected_current_value`.
- Modify: `tests/test_input_validation.py`
  - Cover validation behavior for `expected_current_value`.
- Modify: `tests/test_set_param_dry_run.py`
  - Cover preview shape, `apply_payload`, and session propagation rules.
- Modify: `tests/test_set_param_behavior.py`
  - Cover guarded execute, stale preview refusal, write failure metadata, and top-level `verification_failed`.
- Modify: `tests/test_cross_skill_workflow.py`
  - Cover the actual autonomous loop: inspect -> preview -> replay `apply_payload` -> inspect -> rollback.
- Modify: `tests/fakes.py`
  - Extend the fake engines so they can simulate stale preview, inspect-compatible reads, and post-write verification mismatch cleanly.

### Documentation files

- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `skills/simulink_edit/SKILL.md`
- Modify: `skills/simulink_edit/reference.md`
- Modify: `skills/simulink_edit/test-scenarios.md`
- Modify: `tests/test_docs_contract.py`
- Modify: `tests/test_edit_docs_contract.py`

These docs should describe the guarded loop consistently:

- preview returns `apply_payload`
- execute may require `expected_current_value`
- stale preview returns `precondition_failed`
- verification mismatch returns top-level `verification_failed`
- failures include structured recovery fields

## Chunk 1: Runtime Contract and Workflow Tests

### Task 1: Extend `set_param` schema, parser, and preview contract

**Files:**
- Modify: `simulink_cli/actions/set_param.py`
- Modify: `tests/test_schema_action.py`
- Modify: `tests/test_error_contract.py`
- Modify: `tests/test_json_input_mode.py`
- Modify: `tests/test_input_validation.py`
- Modify: `tests/test_set_param_dry_run.py`

- [ ] **Step 1: Write the failing schema and JSON-mode tests**

Add tests that assert:

```python
def test_set_param_expected_current_value_metadata(self):
    meta = self.schema["actions"]["set_param"]["fields"]["expected_current_value"]
    assert meta["type"] == "string"
    assert meta["required"] is False

def test_parse_json_set_param_with_expected_current_value(self):
    action, args = parse_json_request(
        '{"action":"set_param","target":"m/Gain1","param":"Gain","value":"2.0",'
        '"dry_run":false,"expected_current_value":"1.5"}'
    )
    assert action == "set_param"
    assert args["expected_current_value"] == "1.5"
```

- [ ] **Step 2: Write the failing input-validation and preview-shape tests**

Add tests that assert:

```python
def test_set_param_expected_current_value_uses_payload_validation(self):
    args = {
        "target": "m/B",
        "param": "Gain",
        "value": "2.0",
        "expected_current_value": "",
        "dry_run": False,
        "session": None,
    }
    assert set_param.validate(args) is None

def test_dry_run_output_includes_apply_payload(self):
    result = set_param.execute(_set_param_args(dry_run=True))
    assert result["apply_payload"]["dry_run"] is False
    assert result["apply_payload"]["expected_current_value"] == "1.5"

def test_dry_run_preserves_explicit_session_in_apply_and_rollback(self):
    result = set_param.execute(_set_param_args(dry_run=True, session="MATLAB_12345"))
    assert result["apply_payload"]["session"] == "MATLAB_12345"
    assert result["rollback"]["session"] == "MATLAB_12345"
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
python -m unittest tests.test_schema_action tests.test_error_contract tests.test_json_input_mode tests.test_input_validation tests.test_set_param_dry_run -v
```

Expected:

- FAIL because `expected_current_value` is not in `FIELDS`
- FAIL because `precondition_failed` / `verification_failed` are not aggregated in schema error codes
- FAIL because preview does not return `apply_payload`

- [ ] **Step 4: Implement the minimal schema and preview contract**

Update `simulink_cli/actions/set_param.py` so `FIELDS` and `ERRORS` include the guarded-write contract:

```python
FIELDS = {
    # existing fields...
    "expected_current_value": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Optional guarded-execute precondition from a dry-run preview.",
    },
}

ERRORS = [
    # existing errors...
    "precondition_failed",
    "verification_failed",
]
```

Validation should treat `expected_current_value` like `value`, not like `session`:

```python
for field_name in ("value", "expected_current_value"):
    err = validate_value_field(field_name, args.get(field_name))
    if err is not None:
        return err
```

Preview should now return an executable `apply_payload`:

```python
apply_payload = {
    "action": "set_param",
    "target": target,
    "param": param,
    "value": str(value),
    "dry_run": False,
    "expected_current_value": current_value,
}
if args.get("session") is not None:
    apply_payload["session"] = args["session"]
    rollback["session"] = args["session"]
```

Keep the design explicit:

- do not add hidden preview tokens
- do not modify `core.py` unless a test proves parser behavior needs it

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run:

```bash
python -m unittest tests.test_schema_action tests.test_error_contract tests.test_json_input_mode tests.test_input_validation tests.test_set_param_dry_run -v
```

Expected:

- PASS
- schema shows `expected_current_value`
- preview response includes `apply_payload`
- new error codes appear in `build_schema_payload()["error_codes"]`

- [ ] **Step 6: Commit**

```bash
git add simulink_cli/actions/set_param.py tests/test_schema_action.py tests/test_error_contract.py tests/test_json_input_mode.py tests/test_input_validation.py tests/test_set_param_dry_run.py
git commit -m "feat(edit): add guarded preview contract"
```

### Task 2: Implement guarded execute and structured failure taxonomy

**Files:**
- Modify: `simulink_cli/actions/set_param.py`
- Modify: `tests/test_set_param_behavior.py`
- Modify: `tests/fakes.py`

- [ ] **Step 1: Write the failing guarded-execute tests**

Add tests that assert:

```python
def test_execute_rejects_stale_preview_without_writing(self):
    eng = self._make_engine()
    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        preview = set_param.execute(_set_param_args(dry_run=True))
    eng.force_param_value("my_model/Gain1", "Gain", "9.0")

    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        result = set_param.execute(preview["apply_payload"])

    assert result["error"] == "precondition_failed"
    assert result["details"]["expected_current_value"] == "1.5"
    assert result["details"]["observed_current_value"] == "9.0"
    assert result["details"]["safe_to_retry"] is True
    assert eng.get_param("my_model/Gain1", "Gain") == "9.0"

def test_execute_verification_failure_is_top_level_verification_failed(self):
    eng = VerificationMismatchEngine()
    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        result = set_param.execute(_set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False))
    assert result["error"] == "verification_failed"
```

- [ ] **Step 2: Add failing tests for recovery metadata**

Cover both write-call failure and verification failure:

```python
def test_execute_failure_after_attempt_includes_recovery_metadata(self):
    eng = WriteThenFailEngine()
    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        result = set_param.execute(_set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False))

    assert result["details"]["write_state"] == "attempted"
    assert result["details"]["safe_to_retry"] is False
    assert result["details"]["recommended_recovery"] == "rollback"

def test_verification_failure_includes_recovery_metadata(self):
    eng = VerificationMismatchEngine()
    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        result = set_param.execute(_set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False))

    assert result["details"]["write_state"] == "verification_failed"
    assert result["details"]["safe_to_retry"] is False
    assert result["details"]["recommended_recovery"] == "rollback"
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
python -m unittest tests.test_set_param_behavior -v
```

Expected:

- FAIL because stale preview currently writes or falls through instead of returning `precondition_failed`
- FAIL because verification mismatch still returns `set_param_failed`
- FAIL because structured recovery fields are missing

- [ ] **Step 4: Implement guarded execute and helper error shaping**

Refactor `set_param.execute()` to follow the spec order:

```python
observed_before_write = str(matlab_transport.get_param(eng, target, param)["value"])
expected_current_value = args.get("expected_current_value")

if expected_current_value is not None and observed_before_write != expected_current_value:
    return make_error(
        "precondition_failed",
        "Preview is stale; current value changed before execute.",
        details={
            "target": target,
            "param": param,
            "expected_current_value": expected_current_value,
            "observed_current_value": observed_before_write,
            "write_state": "not_attempted",
            "safe_to_retry": True,
            "recommended_recovery": "rerun_dry_run",
        },
    )
```

On post-attempt failures, return structured machine guidance:

```python
return make_error(
    "verification_failed",
    f"Write could not be verified for parameter '{param}' on '{target}'.",
    details={
        "target": target,
        "param": param,
        "value": str(value),
        "write_state": "verification_failed",
        "rollback": rollback,
        "observed": observed,
        "safe_to_retry": False,
        "recommended_recovery": "rollback",
    },
)
```

Keep `set_param_failed` only for write-call failures. Do not collapse stale preview and verification mismatch into the same top-level code.

- [ ] **Step 5: Extend the fakes instead of inlining test-only hacks**

Add a small helper to `tests/fakes.py`:

```python
class FakeSetParamEngine:
    # existing methods...
    def force_param_value(self, path, param, value):
        self._params[f"{path}::{param}"] = value
```

If needed, add call counters or last-write tracking so tests can prove stale preview refused to mutate.

- [ ] **Step 6: Run the targeted tests to verify they pass**

Run:

```bash
python -m unittest tests.test_set_param_behavior -v
```

Expected:

- PASS
- `precondition_failed` returns before write
- `verification_failed` is a top-level error code
- failure details contain `safe_to_retry` and `recommended_recovery`

- [ ] **Step 7: Commit**

```bash
git add simulink_cli/actions/set_param.py tests/test_set_param_behavior.py tests/fakes.py
git commit -m "feat(edit): guard execute with explicit preconditions"
```

### Task 3: Prove the autonomous loop through cross-skill workflow tests

**Files:**
- Modify: `tests/fakes.py`
- Modify: `tests/test_cross_skill_workflow.py`

- [ ] **Step 1: Write the failing workflow tests against real action modules**

Import `inspect_block` alongside `set_param` and add tests like:

```python
def test_inspect_preview_apply_and_rollback_loop(self):
    eng = FakeCrossSkillEngine()
    inspect_args = {
        "model": None,
        "target": "my_model/Gain1",
        "param": "Gain",
        "active_only": False,
        "strict_active": False,
        "resolve_effective": False,
        "summary": False,
        "session": None,
        "max_params": None,
        "fields": None,
    }

    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        with patch.object(inspect_block, "safe_connect_to_session", return_value=(eng, None)):
            before = inspect_block.execute(inspect_args)
            preview = set_param.execute(_set_param_args(target="my_model/Gain1", param="Gain", value="3.0", dry_run=True))
            execute = set_param.execute(preview["apply_payload"])
            after = inspect_block.execute(inspect_args)

    assert before["value"] == "1.5"
    assert execute["verified"] is True
    assert after["value"] == "3.0"
```

- [ ] **Step 2: Add a stale-preview workflow test**

```python
def test_stale_preview_requires_new_dry_run(self):
    eng = FakeCrossSkillEngine()
    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        preview = set_param.execute(_set_param_args(target="my_model/Gain1", param="Gain", value="3.0", dry_run=True))
    eng.force_param_value("my_model/Gain1", "Gain", "9.0")

    with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
        result = set_param.execute(preview["apply_payload"])

    assert result["error"] == "precondition_failed"
    assert result["details"]["recommended_recovery"] == "rerun_dry_run"
```

- [ ] **Step 3: Run the workflow tests to verify they fail**

Run:

```bash
python -m unittest tests.test_cross_skill_workflow -v
```

Expected:

- FAIL because `FakeCrossSkillEngine` does not yet support `inspect_block.execute()`
- FAIL because the current workflow test does not replay `apply_payload`

- [ ] **Step 4: Upgrade the shared workflow fake, not the production read actions**

Extend `FakeCrossSkillEngine` so it can satisfy `inspect_block.execute()`:

```python
class FakeCrossSkillEngine:
    def get_param(self, path, param):
        if param == "DialogParameters":
            return {"Gain": {}}
        if param == "MaskNames":
            raise RuntimeError("not masked")
        if param == "MaskVisibilities":
            raise RuntimeError("not masked")
        if param == "MaskEnables":
            raise RuntimeError("not masked")
        # existing Handle / value logic

    def fieldnames(self, dialog_params):
        return list(dialog_params.keys())
```

Keep the workflow fake focused on the guarded single-parameter loop; do not turn it into a full scan/connections fake.

- [ ] **Step 5: Run the workflow tests to verify they pass**

Run:

```bash
python -m unittest tests.test_cross_skill_workflow -v
```

Expected:

- PASS
- workflow replays `apply_payload`
- stale preview path is machine-distinguishable
- rollback remains replayable after guarded execute changes

- [ ] **Step 6: Commit**

```bash
git add tests/fakes.py tests/test_cross_skill_workflow.py
git commit -m "test(workflow): cover guarded single-parameter loop"
```

## Chunk 2: Documentation and End-to-End Verification

### Task 4: Align README and `simulink_edit` docs with the guarded loop contract

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `skills/simulink_edit/SKILL.md`
- Modify: `skills/simulink_edit/reference.md`
- Modify: `skills/simulink_edit/test-scenarios.md`
- Modify: `tests/test_docs_contract.py`
- Modify: `tests/test_edit_docs_contract.py`

- [ ] **Step 1: Write the failing docs-contract tests**

Add assertions such as:

```python
def test_reference_md_documents_apply_payload(self):
    text = (EDIT_SKILL_DIR / "reference.md").read_text(encoding="utf-8")
    assert "apply_payload" in text
    assert "expected_current_value" in text

def test_skill_md_contains_precondition_failed(self):
    text = (EDIT_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "precondition_failed" in text
```

Add README-level assertions in `tests/test_docs_contract.py` for:

- `apply_payload`
- `precondition_failed`
- `verification_failed`
- guarded execute wording

Add explicit coverage for the translated and scenario docs too:

- `README.zh-CN.md` must mention the guarded execute flow and `precondition_failed`
- `skills/simulink_edit/test-scenarios.md` must mention preview `apply_payload`, stale-preview rejection, and rollback replay

Use the existing doc contract files directly instead of adding a third docs test module:

- `tests/test_docs_contract.py` should cover `README.md` and `README.zh-CN.md`
- `tests/test_edit_docs_contract.py` should cover `skills/simulink_edit/SKILL.md`, `reference.md`, and `test-scenarios.md`

- [ ] **Step 2: Run the docs tests to verify they fail**

Run:

```bash
python -m unittest tests.test_docs_contract tests.test_edit_docs_contract -v
```

Expected:

- FAIL because current docs still describe preview and execute as loosely related calls
- FAIL because current edit docs do not mention `apply_payload` or `precondition_failed`
- FAIL because verification failure wording still reflects the old contract

- [ ] **Step 3: Update user-facing docs first**

In `README.md` and `README.zh-CN.md`:

- update the safety model bullets to describe guarded execute
- add `precondition_failed` to common error codes
- replace the simple direct execute example with a preview -> replay `apply_payload` flow
- keep the positioning focused on reliability, not new capability breadth

Recommended README wording for the safety model:

```md
- `dry_run` returns both `rollback` and machine-executable `apply_payload`
- execute may include `expected_current_value` to guard against stale previews
- stale preview execute returns `precondition_failed` without mutating the model
- verification mismatch returns `verification_failed` with rollback and recovery metadata
```

- [ ] **Step 4: Update `simulink_edit` docs to describe the actual agent loop**

Update:

- `skills/simulink_edit/SKILL.md`
- `skills/simulink_edit/reference.md`
- `skills/simulink_edit/test-scenarios.md`

Make the examples explicit:

```text
inspect -> set_param (dry_run) -> replay apply_payload -> inspect -> rollback if needed
```

Update the recovery routing so it distinguishes:

- `precondition_failed` -> rerun dry-run
- `set_param_failed` -> inspect constraints / inspect target before retry
- `verification_failed` -> inspect or rollback

- [ ] **Step 5: Run the docs tests to verify they pass**

Run:

```bash
python -m unittest tests.test_docs_contract tests.test_edit_docs_contract -v
```

Expected:

- PASS
- README and skill/reference docs agree on the guarded loop semantics
- docs no longer imply that `verification_failed` is only a write-state detail

- [ ] **Step 6: Commit**

```bash
git add README.md README.zh-CN.md skills/simulink_edit/SKILL.md skills/simulink_edit/reference.md skills/simulink_edit/test-scenarios.md tests/test_docs_contract.py tests/test_edit_docs_contract.py
git commit -m "docs(edit): document guarded agent loop"
```

### Task 5: Final verification, schema check, and live MATLAB smoke

**Files:**
- Modify only if verification exposes issues: `simulink_cli/actions/set_param.py`, `tests/*`, or the edit docs above

- [ ] **Step 1: Run the focused regression suite**

Run:

```bash
python -m unittest tests.test_schema_action tests.test_error_contract tests.test_json_input_mode tests.test_input_validation tests.test_set_param_dry_run tests.test_set_param_behavior tests.test_cross_skill_workflow tests.test_docs_contract tests.test_edit_docs_contract -v
```

Expected:

- PASS
- guarded-loop contract remains stable across schema, runtime, workflow, and docs

- [ ] **Step 2: Run the full repository test suite**

Run:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected:

- PASS
- no unrelated action or release-contract regressions

- [ ] **Step 3: Run plugin-level validation and inspect the shipped schema**

Run:

```bash
claude plugin validate .
python -m simulink_cli schema
```

Expected:

- `claude plugin validate .` -> PASS
- schema output includes `expected_current_value`, `precondition_failed`, and `verification_failed`

- [ ] **Step 4: Run live MATLAB smoke verification for the guarded loop**

Run the preview first and save the returned JSON payload to a temporary file or shell variable:

```bash
python -m simulink_cli --json "{\"action\":\"set_param\",\"target\":\"<real target>\",\"param\":\"<real param>\",\"value\":\"<new value>\",\"dry_run\":true}"
```

Expected:

- success payload includes `apply_payload`
- `apply_payload.expected_current_value` equals the currently observed value
- preview must not mutate the model

Replay the returned `apply_payload` exactly. Do not reconstruct it manually:

```bash
python -m simulink_cli --json '<paste apply_payload captured verbatim from preview response>'
python -m simulink_cli --json "{\"action\":\"inspect\",\"target\":\"<real target>\",\"param\":\"<real param>\"}"
```

Expected:

- execute succeeds with `verified: true`
- inspect confirms the new value

Force a stale preview case:

1. create a new preview with `dry_run:true` and save the full response
2. change the parameter manually in MATLAB or via a separate command
3. replay the stale `apply_payload` captured verbatim from that saved preview response

Expected:

- error `precondition_failed`
- no accidental mutation from the stale preview replay

Replay the returned `rollback` exactly. Do not reconstruct it manually:

```bash
python -m simulink_cli --json '<paste rollback payload captured verbatim from execute or failure response>'
python -m simulink_cli --json "{\"action\":\"inspect\",\"target\":\"<real target>\",\"param\":\"<real param>\"}"
```

Expected:

- rollback execute succeeds
- inspect confirms the original value is restored

- [ ] **Step 5: Commit any verification-driven fixes**

If Step 1-4 required additional code or doc changes:

```bash
git add simulink_cli/actions/set_param.py tests README.md README.zh-CN.md skills/simulink_edit
git commit -m "fix(edit): finish guarded loop verification"
```

If verification required no further edits, do not create an empty commit.
