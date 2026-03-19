---
name: simulink-scan
description: Use when analyzing Simulink model topology, subsystem structure, or effective block parameters in read-only workflows.
---

Use this skill only for Simulink read-only analysis.
Reject write/edit requests (`set_param`, add/delete blocks/lines, save changes).
Visual-only block highlighting via `hilite_system` is allowed because it does not mutate model data.
Canonical skill name is `simulink-scan` (module path `simulink_cli` is internal only).
This skill is one capability inside plugin `simulink-automation-suite`, which is designed to host additional skills over time.

## Preflight

0. Ensure runtime prerequisites:
   - MATLAB Engine for Python is installed in the active Python environment.
   - MATLAB shared session is started by running `matlab.engine.shareEngine` in MATLAB.
1. Discover contract when the caller is uncertain about commands/fields:
   - `python -m simulink_cli schema`
   - JSON: `python -m simulink_cli --json "{\"action\":\"schema\"}"`
2. Discover opened models first:
   - `python -m simulink_cli list_opened`
3. Resolve session strictly:
   - Exact session names only.
   - If multiple sessions exist for MATLAB-bound actions, either run `session use <name>` first or pass explicit `--session`.

## Action Selection

1. Topology/hierarchy analysis -> `scan`
2. Parameter/effective-value analysis -> `inspect`
3. Upstream/downstream signal relationship analysis -> `connections`
4. Visual location in Simulink -> `highlight`
5. Block search by name/type -> `find`
6. Session management -> `session`
7. Capability discovery -> `schema`

Default to shallow scan first, then escalate to recursive/hierarchy only when required.

## Execution Templates

- Shallow scan:
  - `python -m simulink_cli scan --model "<model>"`
- Recursive scan:
  - `python -m simulink_cli scan --model "<model>" --recursive`
- Scan with output controls:
  - `python -m simulink_cli scan --model "<model>" --max-blocks 200 --fields "name,type"`
- Inspect all params with summary:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "All" --summary`
- Inspect with output controls:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "All" --max-params 50 --fields "target,values"`
- Resolve inactive parameter source:
  - `python -m simulink_cli inspect --model "<model>" --target "<block>" --param "<name>" --resolve-effective`
- Analyze upstream/downstream key modules:
  - `python -m simulink_cli connections --target "<block>" --direction both --depth 1 --detail summary`
- Analyze connections with clipping/projection:
  - `python -m simulink_cli connections --target "<block>" --detail ports --max-edges 50 --fields "target,edges,total_edges,truncated"`
- Highlight block in Simulink UI:
  - `python -m simulink_cli highlight --target "<block>"`
- Search blocks by name:
  - `python -m simulink_cli find --model "<model>" --name "PID"`
- Search blocks by type:
  - `python -m simulink_cli find --model "<model>" --block-type "SubSystem"`
- Search with output controls:
  - `python -m simulink_cli find --model "<model>" --name "Controller" --max-results 50 --fields "path,type"`

JSON mode is first-class and mutually exclusive with flag-mode action arguments.

## Recovery Routing

Error-driven next actions:

- `session_required` -> run `session list`, then either `session use <name>` or retry with explicit `--session`.
- `session_not_found` -> rerun `session list`, copy exact name, retry.
- `engine_unavailable` -> install/configure MATLAB Engine for Python for the active interpreter, then retry.
- `no_session` -> run `matlab.engine.shareEngine` in MATLAB, retry.
- `model_required` -> rerun `list_opened`, retry with explicit `--model`.
- `model_not_found` -> rerun `list_opened`, choose existing model.
- `subsystem_not_found` -> run shallow root scan, select valid subsystem.
- `invalid_subsystem_type` -> choose a real SubSystem path.
- `block_not_found` -> run scan, select valid block path.
- `invalid_json` / `json_conflict` / `unknown_parameter` / `invalid_input` -> correct request payload and retry.
- `inactive_parameter` -> use `--resolve-effective` or `--strict-active` according to intent.
- `find` returns empty results → broaden name pattern, try different block_type, or widen scope (remove subsystem constraint).

For full matrix and examples, read `reference.md`.

## Output Discipline

- Ground claims in tool JSON.
- Keep outputs compact: selected model, scan root, recursive flag, key findings.
- Do not dump full recursive trees unless explicitly requested.

## Related Docs

- Deep reference: `reference.md`
- Validation scenarios: `test-scenarios.md`
