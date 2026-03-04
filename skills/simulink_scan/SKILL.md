---
name: simulink_scan
description: Scan and analyze Simulink model structure with low-token, high-reliability workflow. Use for topology checks, subsystem exploration, and parameter inspection.
---

Use plugin-local Python CLI entrypoint (`skills.simulink_scan.scripts.sl_core`) for Simulink analysis based on user request: $ARGUMENTS

Use this skill only when the request is about Simulink model reading/analysis.
Do not use this skill for write/edit actions (add/delete blocks, set params, save changes).

Execution decision tree:
1. Discovery step (always first)
   - Run `python -m skills.simulink_scan.scripts.sl_core list_opened` and parse JSON.
   - If no shared MATLAB session or no opened model is available, return the tool error and next action.

2. Model selection
   - If user explicitly names a model, use `--model "<model>"`.
   - If no model is provided and exactly one model is opened, use that model.
   - If no model is provided and multiple models are opened, avoid deep recursive scan by default; run shallow scan and clearly report selected model plus available alternatives.

3. Scan strategy (token-aware)
   - Default: shallow scan first.
     - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>"`
   - Use recursive scan only when user explicitly asks for deep/internal/hierarchy details or when shallow scan is insufficient.
     - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>" --recursive`
   - If user targets a subsystem, scope scan to subsystem and recurse only when needed.
     - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>" --subsystem "<subsystem>"`
     - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>" --subsystem "<subsystem>" --recursive`

4. Parameter strategy (safe semantics)
   - For broad parameter view:
     - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block_or_subsystem>" --param "All" --summary`
   - For effective-only values:
     - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block_or_subsystem>" --param "All" --active-only`
   - For single parameter correctness:
     - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block_or_subsystem>" --param "<param>" --strict-active`
     - `python -m skills.simulink_scan.scripts.sl_core inspect --model "<model>" --target "<block_or_subsystem>" --param "<param>" --resolve-effective`

Response rules:
- Do not invent model contents; report only from JSON outputs.
- Keep results compact by default. Do not paste full recursive block lists unless user explicitly asks.
- Report concise fields first: selected model, scan_root, recursive flag, block count, key subsystems, and requested focus area findings.
- For large outputs, summarize and cap visible lists (for example, top 10-20 items).

Progressive disclosure:
- Use `reference.md` only when command details or troubleshooting depth is needed.

Error recovery rules:
- If session is missing, surface JSON error and tell user to run `matlab.engine.shareEngine` in MATLAB.
- If model is invalid, rerun `list_opened` and show valid model options.
- If subsystem is invalid, show likely alternatives from shallow scan top-level blocks.
- If parameter is unknown/inactive, use `--summary`, `--strict-active`, or `--resolve-effective` to avoid misinterpretation.
