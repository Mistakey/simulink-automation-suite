# PR2: Schema + Context Controls

Date: 2026-03-07
Branch: `codex/pr2-schema-context`
Merged into: `main`
Merge commit: `ee37069`

## Summary

- Added machine-readable contract introspection action:
  - `schema`
- Added output controls for token discipline:
  - `scan`: `--max-blocks`, `--fields`
  - `inspect`: `--max-params`, `--fields`
- Enforced deterministic ordering for agent repeatability:
  - model list ordering
  - scan block ordering
  - inspect parameter ordering
- Updated docs with schema and output-control examples.

## Key Commits

- `f958353` feat(core): add schema introspection action for agents
- `9160bf0` feat(scan): add output limits and field projection
- `35bbe67` feat(inspect): add deterministic parameter clipping controls
- `05171e1` refactor(output): enforce deterministic ordering for agent repeatability
- `b3e4cc1` docs: add schema and output-control guidance

## Verification

Command:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Result on merged state: 51 tests passed.
