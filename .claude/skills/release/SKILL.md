---
name: release
description: This skill should be used when the user asks to "release a new version", "bump version", "create release tag", "update release notes", "prepare release", or performs any release-related operation for the simulink-automation-suite plugin.
---

# Release

Default release path is **tag-driven GitHub auto release** via `.github/workflows/release.yml`.

## Files to Check First

1. `.claude-plugin/plugin.json`
2. `.claude-plugin/marketplace.json`
3. `simulink_cli/core.py` — `build_schema_payload()["version"]`
4. `docs/release/`
5. `scripts/check_release_metadata.py`
6. `scripts/build_release_notes.py`
7. `.github/workflows/release.yml`

## Release Flow

1. Pick version `X.Y.Z`
2. Update manifests and schema:
   - `.claude-plugin/plugin.json` → `version: "X.Y.Z"`
   - `.claude-plugin/marketplace.json` → `plugins[0].version: "X.Y.Z"`
   - `simulink_cli/core.py` → `build_schema_payload()["version"]` to `"X.Y"` (only when major.minor changes)
   - `docs/release/<date>-vX.Y.Z.md` when required (see Release Notes section)
3. Validate locally:

```bash
python scripts/check_release_metadata.py --tag vX.Y.Z
python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
python scripts/build_release_notes.py --tag vX.Y.Z --ref HEAD
```

4. Archive live test report (if available):
   - If `docs/reports/LIVE-TEST-REPORT.md` exists:
     - Check report's `Test Commit` vs current HEAD
     - If close match: copy to `docs/reports/archive/live-test-vX.Y.Z.md`
     - If large gap: warn "Live test report may be stale" — user decides
     - Reference archived report in release notes Validation section
   - If no report exists: warn "No live test report. Consider running /live-test first." — do not block release

5. Commit release changes
6. Create and push annotated tag:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin <branch>
git push origin vX.Y.Z
```

7. `.github/workflows/release.yml` creates the GitHub Release automatically

## Version Sync Rules

For release version `X.Y.Z`, all four must match:

| Location | Required Value |
|----------|---------------|
| `.claude-plugin/plugin.json` → `version` | `X.Y.Z` |
| `.claude-plugin/marketplace.json` → `plugins[0].version` | `X.Y.Z` |
| `simulink_cli/core.py` → `build_schema_payload()["version"]` | `X.Y` |
| Git tag | `vX.Y.Z` |

`scripts/check_release_metadata.py` enforces this. Any divergence fails validation.

## When To Bump Version

Bump when the change is intended for a distributable release or changes shipped contract behavior.

**Requires bump:**
- `.claude-plugin/**`
- `skills/**`
- `README*`
- `simulink_cli/**`
- tests/docs that define shipped contract behavior

**Does not require bump by itself:**
- `.github/workflows/**`
- `.claude/rules/**`, `.claude/skills/**`
- internal planning/docs not shipped with the plugin

Do not leave shipped behavior changes on an old version with a plan to "bump later".

### CLI Changes and Schema Version

`simulink_cli/core.py` is both the runtime schema source and a release metadata input. When CLI contract changes require a new release version, update schema version with the plugin major.minor rule (e.g., plugin `2.3.4` → schema `"2.3"`).

## Release Notes

### Source Priority

`scripts/build_release_notes.py` writes the GitHub Release body:

1. **Curated**: use `docs/release/` document whose filename matches `vX.Y.Z`
2. **Fallback**: generate deterministic notes from git history (no external AI, commit range from highest earlier semver tag, required sections: Summary, Highlights, Compatibility / Upgrade Notes, Validation)

### When Curated Notes Are Required

- Major or minor release
- Patch that changes user-facing behavior in more than one notable way
- Upgrade or compatibility guidance needed
- Behavior that should be summarized more clearly than raw commit subjects

Optional only for trivial metadata-only or emergency republish cases.

### Bilingual Strategy

Default to a bilingual body in one top-level curated file `docs/release/<date>-vX.Y.Z.md`:

- Full English release notes first
- Chinese section (`## 中文说明`) for user-facing summary, highlights, and compatibility guidance
- Validation may stay English-only

If too long: keep single top-level file with shorter Chinese summary, link to detailed companion at `docs/release/zh-CN/<date>-vX.Y.Z.md`.

Do not add a second top-level version-matching file — `build_release_notes.py` treats multiple matches as an error.

## workflow_dispatch

Use only when:
- The tag already exists
- The original release job failed or was skipped
- The GitHub Release body must be regenerated after fixing docs or scripts

Run from the branch containing the fix. Do not use as the normal first-publish path.

## CI Validation Order

The release workflow runs in this order:

1. `scripts/check_release_metadata.py --tag vX.Y.Z`
2. `python -m unittest discover -s tests -p "test_*.py" -v`
3. `claude plugin validate .` (when available on runner)
4. Fallback validation when `claude` unavailable:
   - `python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v`
   - `python scripts/check_release_metadata.py --tag vX.Y.Z`
5. `scripts/build_release_notes.py`
6. `gh release create` or `gh release edit`

## Change Synchronization

Before releasing, verify all affected artifacts are updated:

**CLI actions/arguments** → update `simulink_cli/core.py` + `simulink_cli/actions/*.py` + tests + `README.md`, `README.zh-CN.md`, `SKILL.md`, `reference.md`

**Error codes** → reuse existing codes; update `simulink_cli/core.py` + docs + `test_error_contract`, `test_runtime_error_mapping`, `test_docs_contract`

**Output budgets** → keep `scan`→`max_blocks,fields`, `inspect`→`max_params,fields`, `connections`→`max_edges,fields`, `find`→`max_results,fields` semantics stable; update output-control tests

**Release metadata** → version-sync per Version Sync Rules above

## Agent Checklist

Before finishing release-related work:

- [ ] Tag format is `vX.Y.Z`
- [ ] Manifest versions match (plugin.json, marketplace.json)
- [ ] Schema version matches plugin major.minor
- [ ] Release notes source is understood (curated vs fallback)
- [ ] Local validation passed
- [ ] No stale docs describing manual-only release flow
- [ ] Live test report reviewed (if available) — no unresolved FAIL items
