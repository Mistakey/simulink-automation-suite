---
name: live-test
description: Execute end-to-end functional testing on real MATLAB/Simulink hardware. Schema-driven discovery makes this version-agnostic — no updates needed when plugin actions change. Use when asked to "run live test", "test on real device", "实机测试", or "/live-test". Supports full, incremental, and targeted re-test modes.
---

# Live Device Testing

End-to-end functional verification of the simulink-automation-suite plugin on real MATLAB/Simulink hardware. This skill tests the plugin as a user would — through its published interface, not its source code.

## Isolation Rules

```
PROHIBITED:
  - Read simulink_cli/ source code
  - Read tests/ unit tests

REQUIRED:
  - Discover available actions via: python -m simulink_cli --json '{"action":"schema"}'
  - Execute all tests via CLI commands
  - Generate test cases dynamically from schema output

ALLOWED:
  - Read skills/simulink_automation/SKILL.md (shipped skill — Phase 5 doc-accuracy target)
  - Read skills/simulink_automation/reference.md (shipped reference doc)
  - Read docs/reports/ (compare with previous reports)
  - Read git log (determine incremental scope)
```

Reading the shipped skill files is a deliberate, scoped exception — the purpose is to verify that documentation actually guides users to correct results.

## Test Mode Selection

When invoked, determine the test mode:

```
Does docs/reports/LIVE-TEST-REPORT.md exist?
├─ No → FULL test (all phases, all actions)
└─ Yes → Read report, extract test_commit and schema snapshot
         Did user request "full"?
         ├─ Yes → FULL test
         └─ No → INCREMENTAL (see Incremental Logic below)

User specifies "retest FAIL-001" or "retest Phase 3"?
└─ TARGETED test (only specified items)
```

### Incremental Logic

```
1. Read test_commit from existing report
2. Run: git log {test_commit}..HEAD --oneline
3. Run: python -m simulink_cli --json '{"action":"schema"}'
4. Compare schema output with Schema Snapshot section in report

Mandatory re-tests:
  - All items with status FAIL
  - All items with status BLOCKED (re-check environment)

AI-judged additions:
  - Commit messages reference specific actions → re-test those action's items
  - skills/simulink_automation/SKILL.md changed → re-test Phase 5
  - Schema output differs from snapshot → re-test Phase 1 + Phase 4
  - Optionally spot-check some PASS items for regression

If changes are large-scale (refactor, new actions added to schema):
  - Suggest full test to user, ask for confirmation
```

## Execution Flow

The action lists per phase below are illustrative for v2.2.0. When the schema reveals actions not listed here, assign them to the appropriate phase based on their characteristics: meta actions → Phase 1, read-only → Phase 2, model lifecycle / write → Phase 3.

### Phase 0: Environment Check (always runs)

```bash
python -m simulink_cli --json '{"action":"session","sub_action":"list"}'
```

- If command fails or returns connection error → ALL items BLOCKED
- Tell user: what failed, how to fix (start MATLAB, install engine, etc.)
- If command succeeds → record MATLAB version, proceed

### Phase 1: Meta Layer

Test meta/discovery actions: `schema`, `session`, `list_opened`

For each action, verify:
- Returns valid JSON (parseable, no raw text on stdout)
- Contains expected top-level fields per schema definition
- Response structure matches schema's declared output

### Phase 2: Read-Only Layer

Test read-only actions: `scan`, `find`, `connections`, `inspect`, `highlight`

Prerequisites: at least one model must be open. If none open, proceed to Phase 3 first to open/create a model, then return to Phase 2.

For `highlight`: limited to verifying success response envelope. Visual verification requires human confirmation — this is a known scope limitation, not an environment block. Note this in the report.

For each action, verify:
- Returns valid JSON with expected fields
- Read-only actions do not mutate model state (verify via list_opened before/after)
- Output control parameters work (max_blocks, max_results, max_edges, max_params, fields)
- Truncation metadata present when results are limited

### Phase 3: Model Lifecycle & Write Layer

Test model lifecycle and write actions: `model_open`, `model_new`, `set_param`, `model_save`

- `model_open`: open an existing .slx file if available; verify it appears in list_opened
- `model_new`: create a temporary model; verify it appears in list_opened
- `set_param`: test the full safety chain:
  1. dry_run=true (default) → verify no actual change, preview returned
  2. dry_run=false → verify parameter changed
  3. Read-back verification via inspect
  4. Rollback value present in response
- `model_save`: save after modifications; verify no errors

### Phase 4: Boundary & Error Handling

For each action discovered via schema:
- Missing required fields → verify error response with appropriate error code
- Wrong parameter types → verify rejection
- Unknown fields → verify rejection (input hardening)
- Unknown action name → verify structured error

Verify:
- All errors return valid JSON (not raw text/stack traces)
- Error codes are stable and documented
- Error messages include actionable suggestions

### Phase 5: Documentation Accuracy

Read `skills/simulink_automation/SKILL.md` and `skills/simulink_automation/reference.md`:
- Follow the documented workflow guidance step by step
- Verify the instructions lead to correct results
- Check that schema field descriptions match actual behavior
- Verify error recovery suggestions are valid and actionable

### Phase 6: Report Generation

Compile all results into the report format defined below. If updating an existing report, follow the Report Update Rules.

## Test Case Generation

For each action discovered via `schema`, generate:

1. **Normal case**: Valid parameters, verify return structure and content
2. **Boundary case**: Omit optional params, use extreme values (e.g., max_blocks=1, depth=0)
3. **Error case**: Missing required fields, wrong types, unknown fields
4. **Workflow case**: Multi-action sequences (e.g., model_new → set_param → inspect → scan)

### Pass/Fail Criteria

**PASS**:
- Returns valid JSON
- Contains all required fields declared in schema
- Behavior matches schema description
- No unexpected side effects (read-only actions don't mutate model state)

**FAIL**:
- Returns non-JSON or parse failure
- Missing required fields
- Behavior contradicts schema description
- Error codes don't match documentation

**BLOCKED**:
- Environment prerequisite unmet, AI cannot resolve

**SKIP**:
- Depends on a BLOCKED item, not attempted

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

## Report Format

Write the report to `docs/reports/LIVE-TEST-REPORT.md`. Create the directory if it does not exist.

Status indicators use text labels as canonical status. Emoji mapping:
- ✅ = All PASS
- ⚠️ = Partial (some FAIL)
- ❌ = Major failure
- 🔒 = BLOCKED
- ⏭️ = SKIP

Use this template:

```markdown
# Live Test Report

## Meta
| Field | Value |
|-------|-------|
| Plugin Version | {from plugin.json} |
| Test Date | {YYYY-MM-DD HH:MM} |
| Test Commit | {git rev-parse --short HEAD} |
| Test Mode | full / incremental / targeted |
| MATLAB Version | {from session response} |
| Simulink Version | {from session response if available} |

## Summary
| Total | Pass | Fail | Blocked | Skip |
|-------|------|------|---------|------|
| {n}   | {n}  | {n}  | {n}     | {n}  |

Phase Coverage:
| Phase | Status |
|-------|--------|
| 0 Environment | {status} |
| 1 Meta | {status} |
| 2 Read-Only | {status} |
| 3 Lifecycle & Write | {status} |
| 4 Error Handling | {status} |
| 5 Documentation | {status} |

## Results

### Phase 1: Meta
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | {test description} | {status} | {commit} | {notes} |

### Phase 2: Read-Only
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|

### Phase 3: Lifecycle & Write
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|

### Phase 4: Error Handling
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|

### Phase 5: Documentation
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|

## Failure Details

### FAIL-{NNN}: {short description}
- **Phase**: {phase number and name}
- **Action**: {action name}
- **Steps**: {exact command executed}
- **Expected**: {what should have happened}
- **Actual**: {what actually happened}
- **Commit**: {commit hash}

## Blocked Details

### BLOCKED-{NNN}: {short description}
- **Phase**: {phase number and name}
- **Reason**: {why it's blocked}
- **Fix**: {suggested fix steps}

## Suggestions

### Bug Fixes
{derived from FAIL items — analyze failure cause, propose fix direction}

### Optimization
{derived from PASS items with anomalies — slow response, redundant data, unclear messages}

### Missing Features
{derived from coverage gaps — common workflows lacking operations, unverifiable capabilities}

## Run History
| Date | Mode | Commit | Result | Notes |
|------|------|--------|--------|-------|
| {date} | {mode} | {commit} | {summary} | {notes} |

## Schema Snapshot
{paste the full schema action output here for incremental comparison}
```

## Report Update Rules (for incremental/targeted re-tests)

- Only modify re-tested rows; leave untouched rows unchanged
- Update the Commit field to current commit for re-tested items
- FAIL → PASS: set Notes to "Fixed in {commit}"
- Resolved FAIL details: prefix title with [RESOLVED in {commit}], keep for history
- Summary and Phase Coverage: always recalculate from current row statuses
- Run History: append a new entry for each test run
- Schema Snapshot: always update to latest schema output

## Suggestions Generation

Observe and record during testing:

**Bug Fixes** (from FAIL items):
- Analyze the failure cause and propose the likely fix direction
- Reference the specific FAIL-NNN for traceability

**Optimization** (from PASS items with anomalies):
- Abnormally slow response times (note the action and duration)
- Redundant or verbose return data
- Unclear or unhelpful error messages
- Inefficient parameter handling patterns

**Missing Features** (from coverage gaps):
- Capabilities declared in schema but not fully verifiable
- Common user workflows that lack necessary operations
- Feature gaps compared to typical Simulink tooling workflows
