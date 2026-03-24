# Report Format & Rules

Write the report to `docs/reports/LIVE-TEST-REPORT.md`. Create the directory if it does not exist.

## Status Indicators

Text labels are canonical. Emoji are optional visual shorthand:

| Emoji | Meaning |
|-------|---------|
| ✅ | All PASS |
| ⚠️ | Partial (some FAIL) |
| ❌ | Major failure |
| 🔒 | BLOCKED |
| ⏭️ | SKIP |

## Report Template

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
