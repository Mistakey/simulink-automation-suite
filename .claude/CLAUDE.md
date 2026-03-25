# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

- Plugin: `simulink-automation-suite` (fixed name, never rename)
- Shipped skill: `simulink-automation` (unified read-only analysis + parameter editing)
- Entrypoint: `python -m simulink_cli`
- Version: synced in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
- Auto release workflow: `.github/workflows/release.yml`

## Commands

```bash
# Run all tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run single test
python -m unittest tests.test_schema_action -v

# Layered validation (recommended during development)
python -m unittest tests.test_schema_action -v
python -m unittest tests.test_json_input_mode tests.test_input_validation -v
python -m unittest tests.test_scan_output_controls tests.test_inspect_output_controls tests.test_connections_output_controls tests.test_find_output_controls -v
python -m unittest tests.test_docs_contract -v

# Manifest validation (when .claude-plugin/ or README* change)
python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v
claude plugin validate .

# Local invocation
python -m simulink_cli schema
python -m simulink_cli --json '{"action":"schema"}'

# Live device testing (requires real MATLAB/Simulink)
# /live-test          — AI judges full vs incremental
# /live-test full     — force full test
# /live-test results  — show latest report
```

## Core Rules

1. **Read-only actions**: `scan`, `inspect`, `find`, `connections`, `highlight` never mutate models.
2. **Write safety**: `set_param` uses `dry_run=true` by default, rollback in every response, read-back verification.
3. **Docs-as-Contract**: code + tests + docs updated together. `test_docs_contract.py` enforces.
4. **Agent-first CLI**: see `simulink_cli/CLAUDE.md` for design philosophy (JSON-first, error envelope, input hardening).
5. **Session matching**: exact-name only, no fuzzy.
6. **Release**: use `/release` skill for version-sync, change synchronization, and release flow.

## On-Demand Context

- **`simulink_cli/CLAUDE.md`** — Agent-first CLI design philosophy. Auto-loads when editing `simulink_cli/` files.
- **`/release` skill** — Version-sync, change synchronization checklist, release notes, validation flow.
- **`/live-test` skill** — End-to-end testing on real MATLAB/Simulink. Schema-driven, incremental, produces reports to `docs/reports/`.

## Git Workflow

- **All development work goes through feature branches** — feat, fix, refactor, docs overhaul, etc. Create a branch (or worktree) first, squash merge to main when complete.
- Direct commits to main only for trivial meta changes (CLAUDE.md edits, typo fixes, release tags).
- Commit freely on the feature branch (TDD granularity is fine).
- Squash merge to main — one commit per logical unit (feat, docs, release).
- Tag and release on main only.

## Engineering Notes

- `.sl_pilot_state.json` is local runtime state (gitignored)
- Most tests use fakes/mocks; no local MATLAB required for unit tests
- Unit tests are necessary but not sufficient for live MATLAB compatibility; live MATLAB smoke verification is still required for transport-sensitive changes
