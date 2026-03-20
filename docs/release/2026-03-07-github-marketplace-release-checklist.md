# GitHub Marketplace Release Checklist

Scope: release `simulink-automation-suite` through the repository's GitHub marketplace and GitHub Release page.
Current manifest version in repo: `2.0.2`.

Default path is **auto release from tag push**. Creating a GitHub Release manually in the web UI is now a fallback, not the recommended workflow.

## 1. Files To Update First

For release `X.Y.Z`, inspect and update in this order:

1. `.claude-plugin/plugin.json` -> `version = X.Y.Z`
2. `.claude-plugin/marketplace.json` -> `plugins[0].version = X.Y.Z`
3. `simulink_cli/core.py` -> schema version `X.Y`
4. `docs/release/<date>-vX.Y.Z.md` when the release needs curated notes
5. `.claude/rules/release.md` only if release policy itself changed

## 2. Release Notes Rules

The auto release workflow uses `scripts/build_release_notes.py`.

Priority:
1. Matching curated release doc under `docs/release/` with `vX.Y.Z` in the filename
2. Deterministic fallback notes generated from git history

Add `docs/release/<date>-vX.Y.Z.md` when:
- release is major or minor
- patch release has multiple user-facing changes
- upgrade guidance or compatibility notes are needed

If the doc is missing, auto release still works; the fallback body includes `Summary`, `Highlights`, `Compatibility / Upgrade Notes`, and `Validation`.

Default curated release-doc style is bilingual:
- keep one top-level curated file at `docs/release/<date>-vX.Y.Z.md`
- put English notes first
- add `## 中文说明` for the Chinese user-facing summary, highlights, and upgrade notes
- `Validation` can stay English-only

If the bilingual body becomes too long:
- keep the main release body in `docs/release/<date>-vX.Y.Z.md`
- keep a short Chinese summary in that main file
- place the full Chinese companion notes under `docs/release/zh-CN/<date>-vX.Y.Z.md`

Do not create a second version-matching top-level markdown file in `docs/release/`; the auto selector expects one curated release doc match.

## 3. Validation Before Tagging

Run at minimum:

```bash
python scripts/check_release_metadata.py --tag vX.Y.Z
python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
python scripts/build_release_notes.py --tag vX.Y.Z --ref HEAD
```

Optional local smoke install:
- `claude --plugin-dir .`

## 4. Auto Release Flow

1. Verify clean working tree and target branch:
   - `git status`
   - `git branch --show-current`
2. Commit release changes:
   - `git add <specific-files>`
   - `git commit -m "chore(release): prepare vX.Y.Z"`
3. Create annotated tag:
   - `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
4. Push branch and tag:
   - `git push origin <branch>`
   - `git push origin vX.Y.Z`
5. `.github/workflows/release.yml` runs automatically and will:
   - validate metadata and tests
   - run `claude plugin validate .` if available, or deterministic fallback checks if not
   - build release notes
   - create or update the GitHub Release

## 5. When To Use `workflow_dispatch`

Use `workflow_dispatch` for auto release backfill only:
- an existing tag did not produce a release
- release notes need regeneration after fixing docs/scripts
- the original release job failed and you need a controlled rerun

When you use `workflow_dispatch`, start it from the branch or commit containing the release automation/doc fix. The workflow checks out that current revision, but still treats the requested tag as the release ref and GitHub Release target.

Do not use `workflow_dispatch` instead of pushing a new tag for a normal release.

## 6. Marketplace Install Examples (User-Facing)

Replace `<owner>/<repo>` with your GitHub repository.

1. Add marketplace in Claude Code:
   - `/plugin marketplace add <owner>/<repo>`
2. Install plugin from that marketplace:
   - `/plugin install simulink-automation-suite@simulink-automation-marketplace`
3. Pull marketplace updates later:
   - `/plugin marketplace update`

## 7. Post-Release Verification

1. In a fresh environment, run:
   - `/plugin marketplace add <owner>/<repo>`
   - `/plugin install simulink-automation-suite@simulink-automation-marketplace`
2. Confirm plugin can run a known command or skill path.
3. If install fails, re-run:
   - `claude plugin validate .`
   - `python scripts/check_release_metadata.py --tag vX.Y.Z`
   - check `.claude-plugin/marketplace.json` path and JSON syntax

## 8. Notes for This Repository

1. Do not assume a specific remote layout; verify publish remotes with `git remote -v` before tagging.
2. This checklist is aligned with current plugin architecture:
   - plugin = suite boundary
   - skill = capability boundary
   - shipped skills are `simulink-scan` and `simulink-edit`
