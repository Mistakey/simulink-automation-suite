# Live Device Testing Skill Design

**Date**: 2026-03-24
**Status**: Approved
**Scope**: New project-level skill for end-to-end live MATLAB/Simulink testing

## Problem Statement

Current test suite uses fakes/mocks — sufficient for contract and regression testing but cannot verify that CLI actions actually work on real MATLAB/Simulink hardware. A systematic, repeatable approach is needed to:

- Validate functionality on real devices
- Produce traceable, incremental test reports
- Detect environment issues vs functional bugs
- Generate actionable improvement suggestions

## Design Decisions

### Project-Level Skill (not Global)

**Decision**: Place at `.claude/skills/live-testing/SKILL.md`

**Why**: Reports must be git-tracked and commit-linked for incremental testing, release integration, and history tracking. Global placement creates an unsolvable "where do reports go?" problem.

**Isolation**: Achieved through behavioral discipline in skill instructions, not physical separation. AI is explicitly prohibited from reading source code or unit tests — must interact only through schema discovery and CLI execution.

### Schema-Driven Discovery (Approach C)

**Decision**: Skill defines testing methodology (phases, report format, quality standards); AI dynamically generates test cases from schema output.

**Why**: Plugin-version-agnostic. New actions automatically discovered via `schema` without skill updates. Balances consistency (fixed process) with flexibility (adaptive content).

### Mixed Model Strategy

**Decision**: AI creates fresh models for some tests, opens existing models for others, uses currently open models when available.

**Why**: Fixed test models create false confidence — if the tool only works on one specific model, that's a bug. AI should adapt to whatever environment is available.

### Living Report + Release Archive

**Decision**: Single `LIVE-TEST-REPORT.md` updated in-place during development; archived to `archive/live-test-v{version}.md` at release time.

**Why**: Avoids file proliferation (vs per-run), supports re-testing without creating new files (vs per-version), while preserving release snapshots for historical reference.

## Skill Architecture

### File Structure

```
.claude/skills/live-testing/
└── SKILL.md

docs/reports/
├── LIVE-TEST-REPORT.md              ← living report, updated in-place
└── archive/
    ├── live-test-v2.2.0.md          ← release snapshot
    └── live-test-v2.3.0.md
```

### Isolation Rules

```
PROHIBITED:
  - Read simulink_cli/ source code
  - Read tests/ unit tests

REQUIRED:
  - Discover actions via `schema` action
  - Execute all tests through CLI commands

ALLOWED:
  - Read SKILL.md (documentation accuracy is a test target)
  - Read docs/reports/ (compare with previous reports)
  - Read git log (determine incremental scope)
```

### Test Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| Full | First run, no existing report, user requests `full` | All phases, all actions |
| Incremental | Default when report exists | AI judges scope from git log + report state |
| Targeted | User specifies (e.g., "retest FAIL-001", "retest Phase 3") | Only specified items |

**Incremental Decision Logic**:

```
Read LIVE-TEST-REPORT.md → extract test_commit
Run git log {test_commit}..HEAD --oneline
Analyze changes:

1. Mandatory re-tests:
   - All FAIL items
   - All BLOCKED items (re-check environment)

2. AI-judged additions:
   - Commit messages referencing specific actions → re-test those
   - SKILL.md changed → re-test Phase 5 (documentation accuracy)
   - Schema definition changed → re-test Phase 1 + Phase 4
   - Optional: spot-check some PASS items for regression

3. Large-scale changes (refactor, new actions):
   - AI suggests full test, asks user for confirmation
```

## Testing Phases

All phases are structurally fixed; test cases within each phase are dynamically generated from schema.

### Phase 0: Environment Check (always runs)

Verify MATLAB reachability and Simulink availability. If unreachable, mark all items BLOCKED with fix instructions and terminate.

### Phase 1: Meta Layer

- `schema` — returns valid JSON, fields complete
- `session` — list / current / use / clear
- `list_opened` — currently open models

### Phase 2: Read-Only Layer

- `model_open` — open existing model
- `scan` — shallow and recursive topology
- `find` — search by name and type
- `connections` — upstream/downstream tracing
- `inspect` — single parameter and full list
- `highlight` — UI highlight

### Phase 3: Write Layer

- `model_new` — create new model
- `set_param` — dry_run → apply → verify → rollback (full safety chain)
- `model_save` — save model

### Phase 4: Boundary & Error Handling

- Invalid parameters, missing required fields, unknown actions
- Verify error codes and messages match schema descriptions

### Phase 5: Documentation Accuracy

- SKILL.md workflow guidance leads to correct results
- Schema descriptions match actual behavior
- Error recovery suggestions are valid and actionable

### Phase 6: Report Generation

- Compile results, write/update report, generate suggestions

**Incremental mode**: AI skips unaffected phases, but Phase 0 always runs.

## Test Case Generation Rules

For each action discovered via `schema`, AI generates:

1. **Normal case**: Valid parameters, verify return structure
2. **Boundary case**: Omit optional params, extreme values
3. **Error case**: Missing required fields, wrong types, unknown fields
4. **Workflow case**: Multi-action sequences (e.g., `model_new` → `set_param` → `inspect` → `scan`)

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

### Test Result States

| State | Meaning |
|-------|---------|
| **PASS** | Executed successfully, result matches expectations |
| **FAIL** | Executed but result incorrect |
| **BLOCKED** | Environment prerequisite unmet, AI cannot resolve |
| **SKIP** | Depends on a BLOCKED item, not attempted |

## Environment Error Handling

```
When environment issue is encountered:
├─ AI can self-resolve (e.g., session not connected → try connecting)
│   └─ Fix and continue testing
└─ AI cannot resolve
    ├─ 1. Pause current test item immediately
    ├─ 2. Inform user:
    │     - What function was being tested
    │     - What environment problem occurred
    │     - Suggested fix steps
    ├─ 3. Mark item as BLOCKED (not FAIL)
    │     Record: block reason + suggested fix
    ├─ 4. Skip subsequent items depending on blocked environment
    └─ 5. Continue testing unaffected items
```

## Report Format

Location: `docs/reports/LIVE-TEST-REPORT.md`

```markdown
# Live Test Report

## Meta
| Field | Value |
|-------|-------|
| Plugin Version | 2.2.0 |
| Test Date | 2026-03-24 14:30 |
| Test Commit | abc1234 |
| Test Mode | full / incremental |
| MATLAB Version | R2024b |
| Simulink Version | 24.2 |

## Summary
| Total | Pass | Fail | Blocked | Skip |
|-------|------|------|---------|------|
| 28    | 24   | 2    | 1       | 1    |

Phase Coverage:
| Phase | Status |
|-------|--------|
| 0 Environment | ✅ |
| 1 Meta | ✅ |
| 2 Read-Only | ⚠️ 1 FAIL |
| 3 Write | ✅ |
| 4 Error Handling | ❌ 1 FAIL |
| 5 Documentation | 🔒 1 BLOCKED |

## Results

### Phase 1: Meta
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | schema returns valid JSON | ✅ PASS | abc1234 | |
| 2 | session list | ✅ PASS | abc1234 | |

### Phase 2: Read-Only
| # | Test | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 4 | scan shallow topology | ✅ PASS | abc1234 | |
| 5 | scan recursive max_depth | ❌ FAIL | abc1234 | See FAIL-001 |

(... other phases ...)

## Failure Details

### FAIL-001: scan recursive ignores max_depth
- **Phase**: 2 Read-Only
- **Action**: scan
- **Steps**: `scan model=test recursive=true max_depth=2`
- **Expected**: Only blocks within 2 levels
- **Actual**: Returned all levels
- **Commit**: abc1234

## Blocked Details

### BLOCKED-001: highlight cannot be verified
- **Phase**: 5 Documentation
- **Reason**: Simulink UI not running in foreground
- **Fix**: Launch Simulink in GUI mode (not -nodisplay)

## Suggestions

### Bug Fixes
- (derived from FAIL items)

### Optimization
- (derived from PASS items with anomalous observations)

### Missing Features
- (derived from test coverage gaps)

## Run History
| Date | Mode | Commit | Result | Notes |
|------|------|--------|--------|-------|
| 2026-03-24 | full | abc1234 | 24✅ 2❌ 1🔒 1⏭️ | Initial |
```

### Report Update Rules

- Only modify re-tested rows; leave others unchanged
- Update Commit field to current commit for re-tested items
- FAIL → PASS: mark Notes as `Fixed in {commit}`
- Resolved FAIL details: prefix with `[RESOLVED in {commit}]`, keep for history
- Summary and Phase Coverage always recalculated
- Append new Run History entry

## Suggestions Generation Rules

AI observes and records during testing:

**Bug Fixes** (from FAIL items):
- Analyze failure cause, propose likely fix direction

**Optimization** (from PASS items with anomalies):
- Abnormally slow response times
- Redundant return data
- Unclear error messages
- Inefficient parameter handling

**Missing Features** (from coverage gaps):
- Capabilities declared in schema but not fully verifiable
- Common user workflows lacking operations
- Feature gaps compared to similar tools

## Release Integration

### Archive Step (added to /release skill)

```
Check docs/reports/LIVE-TEST-REPORT.md exists?
├─ No → Warn: "No live test report. Consider running /live-test first."
│        Do not block release; user decides.
└─ Yes → Check report's test_commit vs current HEAD
         ├─ Match or close → Copy to archive/live-test-v{version}.md
         │                    Reference in release notes
         └─ Large gap → Warn: "Report may be stale." User decides.
```

### Release Notes Reference

```markdown
## Validation
- Unit tests: 218 passed
- Live test report: [docs/reports/archive/live-test-v2.3.0.md](...)
  - 28 tests: 26✅ 0❌ 1🔒 1⏭️
```

## Documentation Updates Required

| Document | Update | Content |
|----------|--------|---------|
| `.claude/CLAUDE.md` | Yes | Add `/live-test` to Commands section |
| `/release` skill | Yes | Add report archive step |
| `README.md` | No | Internal dev tool, not user-facing |
| `agents/` | No | Unrelated to analyzer agent |
| Shipped `SKILL.md` | No | Testing tool is not plugin functionality |

## File Inventory

| File | Action | Purpose |
|------|--------|---------|
| `.claude/skills/live-testing/SKILL.md` | Create | Skill definition with full playbook |
| `docs/reports/LIVE-TEST-REPORT.md` | Generated | Living test report (created by skill execution) |
| `docs/reports/archive/` | Generated | Release snapshots (created by release workflow) |
| `.claude/CLAUDE.md` | Modify | Add `/live-test` command reference |
| `.claude/skills/release/SKILL.md` | Modify | Add report archive step |
