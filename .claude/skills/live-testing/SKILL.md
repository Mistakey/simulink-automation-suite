---
name: live-test
description: Execute end-to-end functional testing on real MATLAB/Simulink hardware. Schema-driven discovery makes this version-agnostic — no updates needed when plugin actions change. Use when asked to "run live test", "test on real device", "实机测试", or "/live-test". Supports full, incremental, and targeted re-test modes.
---

# Live Device Testing

End-to-end functional verification of the simulink-automation-suite plugin on real MATLAB/Simulink hardware. This skill tests the plugin as a user would — through its published interface, not its source code.

## On-Demand References

- **`.claude/skills/live-testing/phases.md`** — Detailed phase definitions, test case generation rules, pass/fail criteria, error handling. Read when starting test execution.
- **`.claude/skills/live-testing/report-template.md`** — Report format, update rules, suggestions generation. Read when writing or updating the report (Phase 6).

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

## Execution Flow Overview

Read `.claude/skills/live-testing/phases.md` for detailed phase definitions before executing.

| Phase | Name | Scope |
|-------|------|-------|
| 0 | Environment Check | MATLAB reachability (always runs) |
| 1 | Meta Layer | `schema`, `session`, `list_opened` |
| 2 | Read-Only Layer | `scan`, `find`, `connections`, `inspect`, `highlight` |
| 3 | Lifecycle & Write | `model_open`, `model_new`, `set_param`, `model_save` |
| 4 | Error Handling | Invalid inputs, error codes, rejection behavior |
| 5 | Documentation | SKILL.md accuracy, schema-behavior consistency |
| 6 | Report | Compile results → `docs/reports/LIVE-TEST-REPORT.md` |

Action lists are illustrative for v2.2.0. When schema reveals unlisted actions, assign by characteristic: meta → Phase 1, read-only → Phase 2, lifecycle/write → Phase 3.

Incremental mode: skip unaffected phases, but Phase 0 always runs.

For report format and update rules, read `.claude/skills/live-testing/report-template.md` during Phase 6.
