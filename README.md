# Simulink Automation Suite

This repository is a Claude Code plugin focused on read-only Simulink analysis via MATLAB Engine for Python.
Canonical plugin/skill name: `simulink-scan`.
Internal Python module path: `skills.simulink_scan` (underscore is module naming only).

## Plugin Root

- Manifest: `.claude-plugin/plugin.json`
- Skill entry: `skills/simulink_scan/SKILL.md`
- Skill deep reference: `skills/simulink_scan/reference.md`
- Runtime scripts: `skills/simulink_scan/scripts/`

## Install and Run

```bash
claude --plugin-dir .
```

or

```bash
claude plugin install . --scope project
```

Invoke:

```text
/simulink-scan:simulink-scan Scan gmp_pmsm_sensored_sil_mdl recursively and focus on controller subsystems.
```

## Direct Python Entry (optional)

```bash
python -m skills.simulink_scan.scripts.sl_core list_opened
python -m skills.simulink_scan.scripts.sl_core scan --model "gmp_pmsm_sensored_sil_mdl"
```

## Strict Mode Defaults (Agent-First)

- Session matching is exact-only. Fuzzy session matching is removed.
- If multiple MATLAB shared sessions are available, you must pass `--session` explicitly for commands that connect to MATLAB.
- Invalid text inputs fail fast with stable JSON errors:
  - `invalid_input`
  - `session_required`
  - `session_not_found`

Examples:

```bash
python -m skills.simulink_scan.scripts.sl_core session list
python -m skills.simulink_scan.scripts.sl_core scan --session "MATLAB_12345" --model "my_model"
```

## Verification

```bash
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
```

## Notes

- stdout is JSON; stderr is human guidance.
- If no MATLAB shared session exists, run `matlab.engine.shareEngine` in MATLAB.
- This project is in development-stage versioning.
