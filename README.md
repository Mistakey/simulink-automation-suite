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
- `sl-pilot session clear`
- `sl-pilot scan [--session MATLAB_12345]`
- `sl-pilot list_opened [--session MATLAB_12345]`
- `sl-pilot highlight --target "Model/BlockPath" [--session MATLAB_12345]`
- `sl-pilot inspect --target "Model/BlockPath" --param "All" [--session MATLAB_12345]`

## Output Rules

- stdout: JSON only.
- stderr: human guidance and warnings.

## Notes

- If no shared MATLAB session exists, run `matlab.engine.shareEngine` in MATLAB.
