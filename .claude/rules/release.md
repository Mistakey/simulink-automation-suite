---
globs: [".claude-plugin/**", "README*"]
---

# Release and Version Bump Rules

> From former AGENTS.md §8 and `docs/release/2026-03-07-github-marketplace-release-checklist.md`.

## Commit-Time Version Discipline

Any commit changing **distributable plugin content** requires a version bump in the same work cycle.

Distributable content: `skills/**`, `.claude-plugin/**`, `README*`, runtime/tests/docs contract files affecting shipped behavior.

Rules:
1. `plugin.json.version` must equal `marketplace.json.plugins[0].version`
2. New version must be higher than previous (semver)
3. "Will bump later when releasing" is **not allowed** for shipped behavior changes

Minimum checks before concluding a commit with distributable changes:

```bash
python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v
claude plugin validate .
```

## Release Checklist

### 1. Version Sync
- Pick version `X.Y.Z`
- Update `.claude-plugin/plugin.json` → `version`
- Update `.claude-plugin/marketplace.json` → `plugins[0].version`
- Verify plugin names consistent across both manifests

### 2. Validation
```bash
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
```

### 3. Tag and Publish
```bash
git status && git branch --show-current
git add <specific-files>
git commit -m "chore(release): bump plugin version to X.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push && git push origin vX.Y.Z
```
Create GitHub Release from tag with key changes and migration notes.

### 4. Post-Release Verification
In a fresh environment:
```bash
/plugin marketplace add <owner>/<repo>
/plugin install simulink-automation-suite@simulink-automation-marketplace
```
Confirm plugin runs a known command.
