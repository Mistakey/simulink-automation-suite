# Connections Action Design

**Date:** 2026-03-08  
**Status:** Approved for planning

## Goal

Add a new read-only `connections` action to `simulink-scan` so agents can locate a target block, highlight it, and retrieve upstream/downstream key modules without writing custom MATLAB scripts.

## Context

Current actions support block scanning, parameter inspection, highlighting, and session management.  
`scan` returns block lists/hierarchy but does not return signal-line connectivity, which causes agents to bypass skill contracts and script direct MATLAB graph queries.

## Scope

- Add a new standalone action: `connections`.
- Keep existing `scan` behavior unchanged.
- Support both flags mode and first-class `--json` mode.
- Maintain read-only boundaries (no model mutation).

Out of scope:

- Automatic model edits or rewiring.
- Replacing existing `scan` output format.

## Action Contract

New action: `connections`

Parameters:

- `model?: str`
- `target: str` (required)
- `session?: str`
- `direction?: str` (`upstream|downstream|both`, default `both`)
- `depth?: int` (default `1`, must be `>0`)
- `detail?: str` (`summary|ports|lines`, default `summary`)
- `include_handles?: bool` (default `false`, effective only when `detail=lines`)

CLI examples:

```bash
python -m skills.simulink_scan connections --target "m/Gain"
python -m skills.simulink_scan connections --target "m/Gain" --direction upstream --depth 2 --detail ports
python -m skills.simulink_scan connections --target "m/Gain" --detail lines --include-handles
```

JSON examples:

```bash
python -m skills.simulink_scan --json "{\"action\":\"connections\",\"target\":\"m/Gain\"}"
python -m skills.simulink_scan --json "{\"action\":\"connections\",\"target\":\"m/Gain\",\"detail\":\"ports\",\"depth\":2,\"direction\":\"both\"}"
```

## Output Design

Default `detail=summary`:

- `target`
- `direction`
- `depth`
- `upstream_blocks`
- `downstream_blocks`

`detail=ports` adds:

- `edges`: list of `{src_block, src_port, dst_block, dst_port, signal_name}`

`detail=lines` adds line-level attributes and only includes `line_handle` when `include_handles=true`.

## Error Contract

Reuse existing stable error codes and envelopes:

- `invalid_input`
- `block_not_found`
- `model_required`
- `model_not_found`
- session-related codes (`session_required`, `session_not_found`, `no_session`, `engine_unavailable`)
- `runtime_error`

No new error codes are required for this phase.

## Architecture

1. Keep `scan` for topology listing only.
2. Add `connections` parser/schema/runtime routing in `sl_core.py`.
3. Add connection traversal in `sl_scan.py` using read-only MATLAB queries.
4. Resolve target path via existing model/target resolution approach.

## Data Flow

1. Resolve target model/path and validate target handle.
2. Traverse upstream/downstream graph using BFS.
3. Respect `direction` and `depth` limits.
4. Use visited-set deduping to avoid cycles/infinite loops.
5. Project results by `detail` level.

## Read-Only and Safety Constraints

- Allowed: `get_param` and connectivity queries.
- Disallowed: `set_param`, save, add/delete blocks/lines.
- Deterministic output ordering and deduping to stabilize agent behavior.

## Testing Plan (Design-Level)

1. Add behavior tests for `connections` traversal and detail projection.
2. Extend schema/json parser tests to include new action/fields.
3. Extend docs contract tests to enforce docs coverage.
4. Keep existing tests green to guarantee backward compatibility.

## Documentation Plan (Design-Level)

Update all user-facing and agent-facing docs:

- `skills/simulink_scan/SKILL.md`
- `skills/simulink_scan/reference.md`
- `skills/simulink_scan/test-scenarios.md`
- `README.md`
- `README.zh-CN.md`

## Alternatives Considered

1. Add connection output into `scan`:
   - Rejected: mixes responsibilities and risks breaking existing flows.
2. Keep script-based ad hoc connectivity queries:
   - Rejected: inconsistent contract and low reproducibility.
3. New standalone `connections` action:
   - Selected: clear contract, backward-compatible, extensible.

## Decision Summary

Use a new `connections` action with defaults optimized for concise answers (`direction=both`, `depth=1`, `detail=summary`) and optional progressive detail controls (`ports`, `lines`, `include_handles`).
