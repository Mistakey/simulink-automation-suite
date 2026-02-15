# Simulink Automation Suite

This repository contains a local CLI bridge from Python to MATLAB/Simulink via `matlab.engine`.

## Purpose

- Provide read-only observability commands for AI tooling.
- Keep machine-facing output parseable as JSON.

## Help for AI Clients

- Run `sl-pilot help` to print `AI_HELP.md`.
- `AI_HELP.md` is the command contract intended for AI agents.

## Core Commands

- `sl-pilot session list`
- `sl-pilot session current`
- `sl-pilot session use MATLAB_12345`
- `sl-pilot session use 62480` (fuzzy match, if unique)
- `sl-pilot session clear`
- `sl-pilot scan [--session MATLAB_12345]`
- `sl-pilot scan --model "gmp_pmsm_sensored_sil_mdl" [--session MATLAB_12345]`
- `sl-pilot scan --model "gmp_pmsm_sensored_sil_mdl" --recursive [--session MATLAB_12345]`
- `sl-pilot scan --model "gmp_pmsm_sensored_sil_mdl" --subsystem "GMP Stanrdard Motor Controller Panel (SIL) Full Edition" [--session MATLAB_12345]`
- `sl-pilot scan --model "gmp_pmsm_sensored_sil_mdl" --hierarchy [--session MATLAB_12345]`
- `sl-pilot list_opened [--session MATLAB_12345]`
- `sl-pilot highlight --target "Model/BlockPath" [--session MATLAB_12345]`
- `sl-pilot inspect --target "Model/BlockPath" --param "All" [--session MATLAB_12345]`
- `sl-pilot inspect --target "Model/BlockPath" --param "All" --active-only [--session MATLAB_12345]`
- `sl-pilot inspect --target "Model/BlockPath" --param "All" --summary [--session MATLAB_12345]`
- `sl-pilot inspect --target "Model/BlockPath" --param "PolePairs" --strict-active [--session MATLAB_12345]`
- `sl-pilot inspect --target "Model/BlockPath" --param "PolePairs" --resolve-effective [--session MATLAB_12345]`
- `sl-pilot inspect --model "gmp_pmsm_sensored_sil_mdl" --target "GMP Stanrdard Motor Controller Panel (SIL) Full Edition" --param "All" [--session MATLAB_12345]`

## Output Rules

- stdout: JSON only.
- stderr: human guidance and warnings.

For `inspect --param All`, output includes `parameter_meta` with `visible`/`enabled`/`active` so inactive fields are explicit.
For `inspect --param <name>`, output includes single-parameter `meta` and optional effective mapping hints when inactive.

## Session Behavior

- `session list` and `session current` expose the effective active session.
- If no session is configured but at least one MATLAB session is open, the first discovered session is auto-selected as active.
- `session use` accepts exact names and unique fuzzy matches (prefix/contains/close match).

## Notes

- If no shared MATLAB session exists, run `matlab.engine.shareEngine` in MATLAB.

## Project Layout

- `sl_core.py`: CLI entrypoint, argparse definitions, and command dispatch.
- `sl_session.py`: MATLAB session discovery/selection/persistence and connect logic.
- `sl_scan.py`: Read-only Simulink operations (`scan`, `inspect`, `highlight`, `list_opened`).
- `sl_common.py`: Shared CLI helpers (`JsonArgumentParser`, JSON emit, list normalization).
