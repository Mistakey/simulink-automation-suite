# Plugin Manifest Schema Notes

This file records practical validator constraints for `.claude-plugin/plugin.json` in this repository.
It is based on known-good public plugin manifests and validator behavior.

## Current Manifest Policy

- Plugin name is product-level: `simulink-automation-suite`.
- Skills represent capability-level boundaries and can grow over time.
- Currently shipped skills are `simulink-scan` and `simulink-edit`.
- Do not describe the full plugin as scan-only.

## Validator-Safe Rules

- Keep `version` present in every manifest revision.
- Keep path-bearing fields as arrays when used (for example `skills`).
- Use explicit file paths for `agents` if agents are added later.
- Do not declare the default `hooks/hooks.json` in `plugin.json`; the CLI may auto-load it.

## Why This Matters

Claude plugin validation is strict and may return generic errors when shape/path assumptions are wrong.
Keeping this manifest explicit and conservative prevents install-time breakage across environments.

## Local Checklist Before Merge

1. Validate JSON shape in `.claude-plugin/plugin.json`.
2. Run `python -m unittest tests/test_plugin_manifest_contract.py -v`.
3. Validate marketplace shape in `.claude-plugin/marketplace.json` when marketplace publishing is enabled.
4. Run `python -m unittest discover -s tests -p "test_*.py" -v`.
5. Optionally run `claude plugin validate .` when CLI is available.
