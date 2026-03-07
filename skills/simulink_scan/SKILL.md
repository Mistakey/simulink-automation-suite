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
2. Choose model:
   - Use explicit `--model` when provided.
   - If multiple models exist and none is specified, surface `model_required` and ask for explicit `--model`.
3. Scan with token control:
   - Default shallow:
     - `python -m skills.simulink_scan.scripts.sl_core scan --model "<model>"`
   - Recursive only if user asks deep/internal/hierarchy or shallow is insufficient.
4. Parameter safety:
   - Prefer `--summary` for overview.
   - Use `--active-only` for effective fields only.
   - Use `--strict-active`/`--resolve-effective` for single-parameter correctness.

Output rules:
- Ground all claims in tool JSON outputs.
- Keep output compact: selected model, scan_root, recursive flag, block count, key findings.
- Do not dump full recursive lists unless explicitly requested.

Recovery rules:
- Missing session: return error and instruct `matlab.engine.shareEngine`.
- Invalid model: rerun list_opened and provide valid options.
- Invalid subsystem: suggest likely top-level alternatives.
- Ambiguous model selection: rerun with explicit `--model`.
- Unknown/inactive param: switch to `--summary`, `--strict-active`, or `--resolve-effective`.

For full command matrix and troubleshooting details, read `reference.md`.
For behavior validation and regression checks, read `test-scenarios.md`.
