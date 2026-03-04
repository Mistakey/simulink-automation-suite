# Simulink Automation Suite

This repository is a Claude Code plugin focused on read-only Simulink analysis via MATLAB Engine for Python.

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
/simulink-scan:simulink_scan Scan gmp_pmsm_sensored_sil_mdl recursively and focus on controller subsystems.
```

## Direct Python Entry (optional)

```bash
python -m skills.simulink_scan.scripts.sl_core list_opened
python -m skills.simulink_scan.scripts.sl_core scan --model "gmp_pmsm_sensored_sil_mdl"
```

## Notes

- stdout is JSON; stderr is human guidance.
- If no MATLAB shared session exists, run `matlab.engine.shareEngine` in MATLAB.
