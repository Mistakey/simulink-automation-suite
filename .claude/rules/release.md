---
globs: [".claude-plugin/**", "README*", ".github/workflows/release.yml", "docs/release/**", "scripts/check_release_metadata.py", "scripts/build_release_notes.py"]
---

# Release and Version Bump Rules

Default release path in this repository is **tag-driven GitHub auto release**. Manual GitHub web-page release authoring is no longer the primary path.

## Agent Guidance Placement

Detailed release policy belongs in this rule file. `.claude/CLAUDE.md` may point agents here and mention the workflow entrypoint, but it should not duplicate the detailed release flow, release notes precedence, or validation checklist.

## Files to Check First

1. `.github/workflows/release.yml`
2. `scripts/check_release_metadata.py`
3. `scripts/build_release_notes.py`
4. `.claude-plugin/plugin.json`
5. `.claude-plugin/marketplace.json`
6. `simulink_cli/core.py`
7. `docs/release/`

## When To Bump Version

Bump plugin version when the change is intended for a distributable release or changes shipped plugin/runtime/docs contract behavior.

Usually includes:
- `.claude-plugin/**`
- `skills/**`
- `README*`
- `simulink_cli/**`
- tests/docs that define shipped contract behavior

Usually does not require a plugin version bump by itself:
- `.github/workflows/**`
- `.claude/rules/**`
- internal planning/docs that do not ship with the plugin bundle

Do not leave shipped behavior changes on an old release version with a plan to "bump later".

## Required Version Sync Rules

For release version `X.Y.Z`:

1. `.claude-plugin/plugin.json.version` must equal `X.Y.Z`
2. `.claude-plugin/marketplace.json.plugins[0].version` must equal `X.Y.Z`
3. `simulink_cli/core.py` → `build_schema_payload()["version"]` must equal `X.Y`
4. Release tag must be exactly `vX.Y.Z`

If any of these diverge, `scripts/check_release_metadata.py` must fail.

## Release Notes Source Priority

`scripts/build_release_notes.py` writes the GitHub Release body with this priority:

1. Use a curated release document from `docs/release/` whose filename matches `vX.Y.Z`
2. If no matching document exists, generate deterministic fallback notes from git history

Fallback generation is intentional and auditable:
- no external AI service
- commit range is computed from the highest earlier semver tag
- required sections are always present: `Summary`, `Highlights`, `Compatibility / Upgrade Notes`, `Validation`

## When `docs/release/<...>.md` Is Required

Add a curated release document when any of these are true:
- release is major or minor
- patch release changes user-facing behavior in more than one notable way
- upgrade or compatibility guidance is needed
- release includes behavior that should be summarized more clearly than raw commit subjects

Curated release docs are optional only for trivial metadata-only or emergency republish cases. If the doc is missing, automation still publishes using fallback notes.

## Bilingual Curated Release Notes

For curated release docs that live at the top level of `docs/release/` and are selected by `scripts/build_release_notes.py`, default to a bilingual body:

- use one top-level curated file: `docs/release/<date>-vX.Y.Z.md`
- keep the full English release notes first
- add a matching Chinese section such as `## 中文说明` for the user-facing summary, highlights, and compatibility guidance
- `Validation` may stay English-only unless the release specifically needs translated operator instructions

If the combined bilingual body becomes too long for the GitHub Release page:

- keep the top-level curated file as the single selected release body
- keep the full English notes there
- include a shorter Chinese summary in the main file
- link to a detailed Chinese companion doc under `docs/release/zh-CN/<date>-vX.Y.Z.md`

Do not add a second top-level version-matching markdown file under `docs/release/`. `scripts/build_release_notes.py` expects a single matching top-level curated release doc and treats multiple matches as an error.

## Default Release Flow

1. Pick `X.Y.Z`
2. Update:
   - `.claude-plugin/plugin.json`
   - `.claude-plugin/marketplace.json`
   - `simulink_cli/core.py` schema version when major.minor changes
   - `docs/release/<date>-vX.Y.Z.md` when required or recommended
3. Validate locally:

```bash
python scripts/check_release_metadata.py --tag vX.Y.Z
python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
python scripts/build_release_notes.py --tag vX.Y.Z --ref HEAD
```

4. Commit release changes
5. Create and push annotated tag:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin <branch>
git push origin vX.Y.Z
```

6. Let `.github/workflows/release.yml` create or update the GitHub Release automatically

## When To Use `workflow_dispatch`

Use `workflow_dispatch` only when:
- the tag already exists
- the original release job failed or was skipped
- the GitHub Release body must be regenerated after fixing docs or release scripts

Run `workflow_dispatch` from the branch or commit that contains the release-doc/script fix you want to publish. The workflow uses that checkout for validation and note selection, but still uses the requested tag as the release ref for git-history calculations and GitHub Release creation.

Do not use `workflow_dispatch` as the normal first publish path when pushing a new release tag is possible.

## GitHub Actions Validation Rules

The release workflow must run, in this order:

1. `scripts/check_release_metadata.py --tag vX.Y.Z`
2. `python -m unittest discover -s tests -p "test_*.py" -v`
3. `claude plugin validate .` when `claude` is available on the runner
4. deterministic fallback validation when `claude` is unavailable:
   - `python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v`
   - `python scripts/check_release_metadata.py --tag vX.Y.Z`
5. `scripts/build_release_notes.py`
6. `gh release create` or `gh release edit`

## Agent Checklist

Before finishing release-related work, confirm:

- release tag format is `vX.Y.Z`
- manifest versions match
- schema version matches plugin major.minor
- release notes source is understood
- minimum validation set ran
- any stale docs still describing manual-only release flow were updated
