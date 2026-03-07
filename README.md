# Simulink Automation Suite

This repository is a Claude Code plugin for Simulink automation workflows via MATLAB Engine for Python.
Canonical plugin name: `simulink-automation-suite`.
Current shipped skill: `simulink-scan` (read-only analysis).
Internal Python module path for the current skill runtime: `skills.simulink_scan` (underscore is module naming only).

## Plugin Root

- Manifest: `.claude-plugin/plugin.json`
- Current skill entry: `skills/simulink_scan/SKILL.md`
- Current skill deep reference: `skills/simulink_scan/reference.md`
- Current runtime scripts: `skills/simulink_scan/scripts/`

## Suite Positioning

- Product boundary: this plugin is the Simulink automation suite.
- Skill boundary: each capability can be implemented as an independent skill.
- Current capability set: scan/inspect/session via `simulink-scan`.
- Planned capability growth: future skills can add edit/build/repair workflows without renaming the plugin.
- This release does not split shared Python core yet; runtime refactoring and MCP-core migration are future work.

## Install and Run

```bash
claude --plugin-dir .
```

or

```bash
claude plugin install . --scope project
```

## GitHub Marketplace Publishing

This repository now includes `.claude-plugin/marketplace.json` so it can be used as a GitHub-hosted Claude Code marketplace source.
Marketplace name: `simulink-automation-marketplace`.
Published plugin entry: `simulink-automation-suite` from repo root (`source: "./"`).

Invoke:

```text
/simulink-automation-suite:simulink-scan Scan gmp_pmsm_sensored_sil_mdl recursively and focus on controller subsystems.
```

## Direct Python Entry (optional)

```bash
python -m skills.simulink_scan schema
python -m skills.simulink_scan list_opened
python -m skills.simulink_scan scan --model "gmp_pmsm_sensored_sil_mdl"
```

## Strict Mode Defaults (Agent-First)

- Session matching is exact-only. Fuzzy session matching is removed.
- If multiple MATLAB shared sessions are available, you must pass `--session` explicitly for commands that connect to MATLAB.
- Invalid text inputs fail fast with stable JSON errors:
  - `invalid_input`
  - `session_required`
  - `session_not_found`
  - `model_not_found`
  - `subsystem_not_found`
  - `invalid_subsystem_type`
  - `block_not_found`
- `--json` is a first-class request entrypoint and is mutually exclusive with flag-based input.

Error envelope:

```json
{
  "error": "<stable_code>",
  "message": "<human_readable_message>",
  "details": {},
  "suggested_fix": "<optional_next_step>"
}
```

Examples:

```bash
python -m skills.simulink_scan session list
python -m skills.simulink_scan scan --session "MATLAB_12345" --model "my_model"
```

JSON request examples:

```bash
python -m skills.simulink_scan --json "{\"action\":\"schema\"}"
python -m skills.simulink_scan --json "{\"action\":\"list_opened\",\"session\":\"MATLAB_12345\"}"
python -m skills.simulink_scan --json "{\"action\":\"scan\",\"model\":\"my_model\",\"recursive\":true,\"session\":\"MATLAB_12345\"}"
```

Output controls:

```bash
python -m skills.simulink_scan scan --model "my_model" --max-blocks 200 --fields "name,type"
python -m skills.simulink_scan inspect --model "my_model" --target "my_model/Gain" --param "All" --max-params 50 --fields "target,values"
```

JSON strictness:

- Do not mix `--json` with other action flags.
- Unknown JSON fields return `unknown_parameter`.
- Malformed JSON or wrong field types return `invalid_json`.

## Verification

```bash
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
```

## Notes

- stdout is JSON; stderr is human guidance.
- If no MATLAB shared session exists, run `matlab.engine.shareEngine` in MATLAB.
- This project is in development-stage versioning.
