# GitHub Marketplace Release Checklist

Scope: release `simulink-automation-suite` through GitHub-hosted Claude Code marketplace.
Current manifest version in repo: `1.2.0`.

## 1. Version Sync

1. Pick release version `X.Y.Z` (for example `1.2.0`).
2. Update plugin manifest version:
   - `.claude-plugin/plugin.json` -> `version`
3. Update marketplace plugin entry version:
   - `.claude-plugin/marketplace.json` -> `plugins[0].version`
4. Ensure plugin names stay consistent:
   - `.claude-plugin/plugin.json` -> `name`
   - `.claude-plugin/marketplace.json` -> `plugins[0].name`
5. Update release notes/changelog docs if used by your workflow.

## 2. Validation Before Tagging

1. Run tests:
   - `python -m unittest discover -s tests -p "test_*.py" -v`
2. Validate plugin + marketplace manifests:
   - `claude plugin validate .`
3. Optional local smoke install:
   - `claude --plugin-dir .`

## 3. Git Tag and Publish Flow

1. Verify clean working tree and correct branch:
   - `git status`
   - `git branch --show-current`
2. Commit release changes:
   - `git add .`
   - `git commit -m "release: vX.Y.Z"`
3. Create annotated tag:
   - `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
4. Push branch and tag:
   - `git push`
   - `git push origin vX.Y.Z`
5. Create GitHub Release from tag `vX.Y.Z`:
   - title: `vX.Y.Z`
   - notes: key changes + any migration notes

## 4. Marketplace Install Examples (User-Facing)

Replace `<owner>/<repo>` with your GitHub repository.

1. Add marketplace in Claude Code:
   - `/plugin marketplace add <owner>/<repo>`
2. Install plugin from that marketplace:
   - `/plugin install simulink-automation-suite@simulink-automation-marketplace`
3. Pull marketplace updates later:
   - `/plugin marketplace update`

## 5. Post-Release Verification

1. In a fresh environment, run:
   - `/plugin marketplace add <owner>/<repo>`
   - `/plugin install simulink-automation-suite@simulink-automation-marketplace`
2. Confirm plugin can run a known command/skill path.
3. If install fails, re-run:
   - `claude plugin validate .`
   - check `.claude-plugin/marketplace.json` path and JSON syntax.

## 6. Notes for This Repository

1. This repository currently has no `origin` remote configured locally, so release commands assume remote setup is completed first.
2. This checklist is aligned with current plugin architecture:
   - plugin = suite boundary
   - skill = capability boundary
   - current released skill is `simulink-scan`
