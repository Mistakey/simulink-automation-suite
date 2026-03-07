---
name: simulink-scan
description: Use when analyzing Simulink model topology, subsystem structure, or effective block parameters in read-only workflows.
---

Use this skill only for Simulink read-only analysis.
Reject write/edit requests (set_param, add/delete blocks/lines, save changes).
Canonical skill name is `simulink-scan` (module path `skills.simulink_scan` is internal only).

Decision flow:
1. Discover models first:
   - `python -m skills.simulink_scan.scripts.sl_core list_opened`
   - JSON mode alternative:
     - `python -m skills.simulink_scan.scripts.sl_core --json "{\"action\":\"list_opened\"}"`
2. Resolve session strictly:
   - Use exact session names only (no fuzzy matching).
   - If multiple sessions exist for commands that connect to MATLAB, require explicit `--session`.
   - If exact session does not exist, surface `session_not_found`.
   - For malformed text inputs, surface `invalid_input`.
3. Choose model:
   - Use explicit `--model` when provided.
   - If multiple models exist and none is specified, surface `model_required` and ask for explicit `--model`.
4. Scan with token control:
   - Default shallow:
     - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>"`
     - `python -m skills.simulink_scan.scripts.sl_core --json "{\"action\":\"scan\",\"model\":\"<model>\",\"session\":\"<session>\"}"`
   - Recursive only if user asks deep/internal/hierarchy or shallow is insufficient.
5. Parameter safety:
   - Prefer `--summary` for overview.
   - Use `--active-only` for effective fields only.
   - Use `--strict-active`/`--resolve-effective` for single-parameter correctness.

Output rules:
- Ground all claims in tool JSON outputs.
- Keep output compact: selected model, scan_root, recursive flag, block count, key findings.
- Do not dump full recursive lists unless explicitly requested.

Recovery rules:
- Missing session: return error and instruct `matlab.engine.shareEngine`.
- Multiple sessions without explicit `--session`: return `session_required`.
- Non-exact session name: return `session_not_found`.
- Invalid text fields (`?`, `#`, `%`, control chars, trim mismatch, overlength): return `invalid_input`.
- JSON and flags mixed in one call: return `json_conflict`.
- Unknown JSON fields: return `unknown_parameter`.
- Malformed JSON or wrong JSON value type: return `invalid_json`.
- Invalid model: return `model_not_found`, then rerun list_opened and provide valid options.
- Invalid subsystem path: return `subsystem_not_found` and suggest likely top-level alternatives.
- Non-subsystem path passed as subsystem: return `invalid_subsystem_type`.
- Invalid inspect target path: return `block_not_found`.
- Ambiguous model selection: rerun with explicit `--model`.
- Unknown/inactive param: switch to `--summary`, `--strict-active`, or `--resolve-effective`.

For full command matrix and troubleshooting details, read `reference.md`.
For behavior validation and regression checks, read `test-scenarios.md`.
