# Simulink Scan Skill Reference

This file is optional deep reference for the `simulink_scan` skill.

## JSON Contract

- stdout is machine-readable JSON.
- stderr is human guidance and warnings.

## Session Behavior

- Session priority: explicit `--session` > saved active session > first discovered session.
- Session management actions:
  - `python -m skills.simulink_scan.scripts.sl_core session list`
  - `python -m skills.simulink_scan.scripts.sl_core session current`
  - `python -m skills.simulink_scan.scripts.sl_core session use MATLAB_12345`
  - `python -m skills.simulink_scan.scripts.sl_core session clear`

## Scan Actions

- Shallow scan:
  - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>"`
- Recursive scan:
  - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>" --recursive`
- Subsystem scan:
  - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>" --subsystem "<subsystem>" --recursive`
- Hierarchy output:
  - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>" --hierarchy`

## Inspect Actions

- Full parameter view:
  - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block>" --param "All"`
- Active-only parameters:
  - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block>" --param "All" --active-only`
- Summary mode:
  - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block>" --param "All" --summary`
- Strict active check:
  - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block>" --param "<name>" --strict-active`
- Resolve effective value:
  - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block>" --param "<name>" --resolve-effective`

## Troubleshooting

- If no shared MATLAB session is found, run `matlab.engine.shareEngine` in MATLAB.
- If `matlab.engine` import fails, install/configure MATLAB Engine for Python in the active environment.
