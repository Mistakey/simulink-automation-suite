# Agent-First CLI Optimization TODO (P1-P3)

Date: 2026-03-07
Owner: Codex + user
Status: In Progress

## Milestones

- [x] M0 Design approved and persisted
  - [x] Create design doc: `2026-03-07-agent-first-cli-optimization-design.md`
- [ ] M1 PR1 complete: Unified error contract
  - [ ] Implement centralized error helpers
  - [ ] Migrate `sl_core.py` error mapping
  - [ ] Migrate `sl_scan.py` error returns
  - [ ] Migrate `sl_session.py` no-session/state errors
  - [ ] Add/adjust tests for stable error envelope
  - [ ] Run full tests and prepare PR1
- [ ] M2 PR2 complete: Schema + context controls + deterministic ordering
  - [ ] Add schema/introspection action
  - [ ] Add output limit/field controls for scan/inspect
  - [ ] Add deterministic sorting for models/blocks/params
  - [ ] Add tests for schema and clipping behavior
  - [ ] Run full tests and prepare PR2
- [ ] M3 PR3 complete: Skill/reference agent-first refactor
  - [ ] Rewrite `SKILL.md` into composable runbook structure
  - [ ] Add error-code recovery matrix in `reference.md`
  - [ ] Align `README.md` and `test-scenarios.md`
  - [ ] Add lightweight docs-consistency checks
  - [ ] Run full tests and prepare PR3
- [ ] M4 Final verification
  - [ ] Re-run full test suite on final branch
  - [ ] Confirm docs-code consistency
  - [ ] Summarize merged behavior changes

## PR Order (Serial)

1. `codex/pr1-error-contract`
2. `codex/pr2-schema-context`
3. `codex/pr3-skill-refactor`

## Rules

1. No cross-PR feature mixing.
2. Each PR must pass `python -m unittest discover -s tests -p "test_*.py" -v`.
3. Each PR updates affected docs in the same branch.
