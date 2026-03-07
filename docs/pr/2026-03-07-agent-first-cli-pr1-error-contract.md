# PR1: Unified Error Contract

Date: 2026-03-07
Branch: `codex/pr1-error-contract`
Merged into: `main`
Merge commit: `d84a6fd`

## Summary

- Added centralized error helper module:
  - `skills/simulink_scan/scripts/sl_errors.py`
- Normalized core/session/scan failure outputs to stable machine fields:
  - `error`
  - `message`
  - `details`
  - optional `suggested_fix`
- Updated docs to reflect the new error contract:
  - `README.md`
  - `skills/simulink_scan/SKILL.md`
  - `skills/simulink_scan/reference.md`

## Key Commits

- `da6addd` feat(errors): add stable error payload helpers
- `053c442` refactor(session): normalize session error payloads
- `44353cb` refactor(scan): convert scan and inspect failures to stable error codes
- `1327e74` refactor(core): enforce stable top-level error contract
- `8a4a6fa` docs: document unified error contract

## Verification

Command:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Result on merged state: 40 tests passed.
