# sl-pilot AI Help

Use this file as machine-facing command guidance.

## Output Contract

- Standard output (stdout) is always JSON.
- Human guidance and warnings are printed to stderr.

## Session Model

- `sl-pilot session use <name>` sets the active MATLAB session for future commands.
- `sl-pilot session use <name>` supports fuzzy matching when the input uniquely maps to one session.
- `sl-pilot scan`, `highlight`, `inspect`, and `list_opened` use the active session automatically.
- You can override once with `--session <name>` on the command itself.
- Session priority is: explicit `--session` > saved active session > first discovered session.
- `session list` and `session current` report the effective active session even when auto-selected.

## Commands

- `sl-pilot session list`
  - List available shared MATLAB sessions.

- `sl-pilot session current`
  - Show effective active session, source (`saved` or `auto`), and configured session.

- `sl-pilot session use MATLAB_12345`
  - Save active session for subsequent commands.

- `sl-pilot session use 62480`
  - Fuzzy example: unique suffix/prefix/contains match to `MATLAB_62480`.

- `sl-pilot session clear`
  - Clear saved active session.

- `sl-pilot scan [--session MATLAB_12345]`
  - Return active model topology JSON.

- `sl-pilot list_opened [--session MATLAB_12345]`
  - List loaded block diagrams.

- `sl-pilot highlight --target "Model/BlockPath" [--session MATLAB_12345]`
  - Highlight a block.

- `sl-pilot inspect --target "Model/BlockPath" --param "All" [--session MATLAB_12345]`
  - Return available dialog parameter keys and values.

- `sl-pilot inspect --target "Model/BlockPath" --param "Gain" [--session MATLAB_12345]`
  - Return one specific parameter value.

## Troubleshooting

- If you get `No shared MATLAB session found`, ask the user to run
  `matlab.engine.shareEngine` in MATLAB Command Window.
