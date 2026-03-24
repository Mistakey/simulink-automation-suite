# Test Phases & Execution Rules

## Phase 0: Environment Check (always runs)

```bash
python -m simulink_cli --json '{"action":"session","sub_action":"list"}'
```

- If command fails or returns connection error → ALL items BLOCKED
- Tell user: what failed, how to fix (start MATLAB, install engine, etc.)
- If command succeeds → record MATLAB version, proceed

## Phase 1: Meta Layer

Test meta/discovery actions: `schema`, `session`, `list_opened`

For each action, verify:
- Returns valid JSON (parseable, no raw text on stdout)
- Contains expected top-level fields per schema definition
- Response structure matches schema's declared output

## Phase 2: Read-Only Layer

Test read-only actions: `scan`, `find`, `connections`, `inspect`, `highlight`

Prerequisites: at least one model must be open. If none open, proceed to Phase 3 first to open/create a model, then return to Phase 2.

For `highlight`: limited to verifying success response envelope. Visual verification requires human confirmation — this is a known scope limitation, not an environment block. Note this in the report.

For each action, verify:
- Returns valid JSON with expected fields
- Read-only actions do not mutate model state (verify via list_opened before/after)
- Output control parameters work (max_blocks, max_results, max_edges, max_params, fields)
- Truncation metadata present when results are limited

## Phase 3: Model Lifecycle & Write Layer

Test model lifecycle and write actions: `model_open`, `model_new`, `set_param`, `model_save`

- `model_open`: open an existing .slx file if available; verify it appears in list_opened
- `model_new`: create a temporary model; verify it appears in list_opened
- `set_param`: test the full safety chain:
  1. dry_run=true (default) → verify no actual change, preview returned
  2. dry_run=false → verify parameter changed
  3. Read-back verification via inspect
  4. Rollback value present in response
- `model_save`: save after modifications; verify no errors

## Phase 4: Boundary & Error Handling

For each action discovered via schema:
- Missing required fields → verify error response with appropriate error code
- Wrong parameter types → verify rejection
- Unknown fields → verify rejection (input hardening)
- Unknown action name → verify structured error

Verify:
- All errors return valid JSON (not raw text/stack traces)
- Error codes are stable and documented
- Error messages include actionable suggestions

## Phase 5: Documentation Accuracy

Read `skills/simulink_automation/SKILL.md` and `skills/simulink_automation/reference.md`:
- Follow the documented workflow guidance step by step
- Verify the instructions lead to correct results
- Check that schema field descriptions match actual behavior
- Verify error recovery suggestions are valid and actionable

## Phase 6: Report Generation

Compile all results into the report. Read `.claude/skills/live-testing/report-template.md` for format and rules.

---

## Test Case Generation

For each action discovered via `schema`, generate:

1. **Normal case**: Valid parameters, verify return structure and content
2. **Boundary case**: Omit optional params, use extreme values (e.g., max_blocks=1, depth=0)
3. **Error case**: Missing required fields, wrong types, unknown fields
4. **Workflow case**: Multi-action sequences (e.g., model_new → set_param → inspect → scan)

### Pass/Fail Criteria

**PASS**: Returns valid JSON, contains all required fields, behavior matches schema, no unexpected side effects

**FAIL**: Non-JSON response, missing fields, behavior contradicts schema, error codes don't match docs

**BLOCKED**: Environment prerequisite unmet, AI cannot resolve

**SKIP**: Depends on a BLOCKED item, not attempted

---

## Environment Error Handling

When an environment issue is encountered during any test:

1. If AI can self-resolve (e.g., no session → try connecting): fix and continue
2. If AI cannot resolve:
   - Pause the current test item immediately
   - Tell the user:
     - What function was being tested
     - What environment problem occurred
     - Suggested fix steps
   - Mark item as BLOCKED (not FAIL) with reason and fix suggestion
   - Skip subsequent items that depend on the blocked environment
   - Continue testing unaffected items

## Timeout Handling

If a CLI command does not return within 60 seconds:
- Mark the test item as BLOCKED with reason "Command timed out after 60s"
- Suggest the user check MATLAB responsiveness
- Continue with remaining tests that don't depend on the timed-out action

## Test Cleanup

After all testing completes:
- Note any models that were opened or created during testing
- Inform user which models/files may need manual cleanup
- If temporary .slx files were created by model_new, note their locations for deletion
- model_close is not available as a CLI action — document this as a known limitation
