# Backlog Remaining Items — Design Spec

**Date**: 2026-03-29
**Status**: Design approved, pending implementation
**Branch**: `fix/backlog-quick-wins`
**Backlog refs**: FEAT-002b, FEAT-004, FEAT-005

---

## Overview

Three remaining backlog items from the FOC model building exercise (2026-03-29). The quick-fix items (IMPROVE-001, PAIN-001/002, DOC-001/002/003) and straightforward features (FEAT-001, FEAT-002a, FEAT-003) are already implemented and committed on the branch.

This spec covers:

1. **FEAT-002b**: `simulate` stores results in MATLAB workspace
2. **FEAT-004**: New `sim-analyst` subagent for simulation data analysis
3. **FEAT-005**: Batch mode for `block_add` and `line_add`

---

## 1. FEAT-002b: simulate stores results in workspace

### Motivation

After `simulate` runs, the `SimulationOutput` object is discarded. There is no way to access simulation data (logged signals, workspace variables) through the plugin. This blocks all post-simulation analysis workflows.

### Design

Modify `matlab_transport.sim()` to execute simulation via `evalc` and store the result in a known base workspace variable.

**MATLAB code executed internally:**

```matlab
sl_sim_result = sim('model', 'StopTime', '1.0');
assignin('base', 'sl_sim_result', sl_sim_result);
```

**Variable name**: `sl_sim_result` (prefixed with `sl_` to avoid collisions with user variables).

**Response changes**: None. The `simulate` action response stays identical (`action`, `model`, `warnings`, `overrides`, `timeout`). The workspace variable is a side effect, not a return value.

**Fallback**: If `assignin` fails (unlikely), the simulation itself still succeeds. The warning is added to the `warnings` array. The agent can then use `matlab_eval` to manually save results.

### Impact

- `simulate_cmd.py`: After `matlab_transport.sim()` returns, call `matlab_transport.eval_code()` to run `assignin('base','sl_sim_result', sl_sim_result)`. This preserves the existing `sim()` behavior (including the FEAT-002a async timeout) and adds storage as a post-step.
- `matlab_transport.py`: No change to `sim()` itself. Storage is a separate `eval_code` call.
- Tests: Update `FakeModelEngine` to track workspace assignments.
- SKILL.md: Document `sl_sim_result` availability after simulate.

---

## 2. FEAT-004: `sim-analyst` subagent

### Motivation

Post-simulation analysis requires reading potentially massive waveform data (millions of data points). Returning raw data to the main agent would blow up the context window. A dedicated subagent absorbs the data in its own context and returns only conclusions.

### Design

**Agent definition** (`agents/sim-analyst.md`):

| Field | Value |
|-------|-------|
| name | `sim-analyst` |
| description | Dispatched for post-simulation data analysis — signal extraction, dynamic performance evaluation, waveform comparison. Writes and executes analysis code (MATLAB/Python), returns conclusions without exposing raw data to the main conversation. |
| model | sonnet |
| color | green |
| tools | Bash, Write, Read, Grep, Glob |

**Scope**: Read-only. Does not execute `set_param`, `simulate`, `model_new`, `model_open`, `model_save`, or any model mutation.

**Analysis means** (dual):

1. **matlab_eval via CLI** — for quick checks:
   ```
   python -m simulink_cli --json '{"action":"matlab_eval","code":"speed=sl_sim_result.logsout.get(\"speed\").Values; fprintf(\"end=%.1f max=%.1f\\n\",speed.Data(end),max(speed.Data))"}'
   ```

2. **Python scripts via Write + Bash** — for complex analysis (numpy/scipy/matplotlib):
   The agent writes a Python script to a temp file, executes via Bash, and reads the printed output.
   This path is for tasks like FFT, frequency response, statistical analysis, or plotting.

**Dispatch protocol**: Main agent provides session, model, and analysis goal:

```
Analyze the simulation results of FOC_Basic:
- Check whether rotor speed tracks the 500 rpm reference
- Report rise time, overshoot, settling time, steady-state error
Session: MATLAB_R2024b, Model: FOC_Basic
```

**Output format**: Same 6-section envelope as `simulink-analyzer`:

```
## Context
## Answer
## Evidence
## Actions Performed
## Limitations
## Suggested Followup
```

### Relationship to simulink-analyzer

| Aspect | simulink-analyzer | sim-analyst |
|--------|-------------------|-------------|
| Analyzes | Model structure (topology, connections, parameters) | Simulation data (signals, waveforms, performance) |
| Data source | CLI read actions (scan, inspect, find, connections) | `sl_sim_result` workspace variable via matlab_eval / Python |
| Tools | Bash, Read, Grep, Glob | Bash, **Write**, Read, Grep, Glob |
| Write capability | None (read-only) | Writes analysis scripts only (not model mutations) |

### Registration

- Add `agents/sim-analyst.md` to the repo
- Register in `.claude-plugin/plugin.json` agents array
- Add to SKILL.md Responsibility & Handoff section

---

## 3. FEAT-005: Batch mode for block_add and line_add

### Motivation

Building models requires adding 20+ blocks and 30+ lines. Each individual `block_add` / `line_add` call costs ~200 tokens (request + response). Batch mode reduces 20 calls to 1, saving significant token budget.

### Design: Extend existing actions

No new actions. `block_add` and `line_add` gain an array field for batch mode.

#### block_add — batch fields

| Field | Type | Description |
|-------|------|-------------|
| `blocks` | array | Array of `{source, destination, position?}` objects. Mutually exclusive with `source`/`destination`. |

When `blocks` is present, `source` and `destination` must be absent (and vice versa). Validation rejects mixed usage.

**Single mode** (unchanged):
```json
{"action": "block_add", "source": "simulink/Gain", "destination": "m/Gain1"}
```

**Batch mode** (new):
```json
{"action": "block_add", "blocks": [
  {"source": "simulink/Gain", "destination": "m/Gain1"},
  {"source": "simulink/Sum", "destination": "m/Sum1", "position": [200, 100, 230, 130]}
]}
```

Note: Model is derived from the first item's `destination` path (same as single mode). All items must target the same model; mixed-model batches are rejected. The `auto_layout` field applies after all blocks are added.

#### line_add — batch fields

| Field | Type | Description |
|-------|------|-------------|
| `lines` | array | Array of `{src_block, src_port, dst_block, dst_port}` objects. Mutually exclusive with individual `src_block`/`src_port`/`dst_block`/`dst_port`. |

**Single mode** (unchanged):
```json
{"action": "line_add", "model": "m", "src_block": "A", "src_port": 1, "dst_block": "B", "dst_port": 1}
```

**Batch mode** (new):
```json
{"action": "line_add", "model": "m", "lines": [
  {"src_block": "A", "src_port": 1, "dst_block": "B", "dst_port": 1},
  {"src_block": "B", "src_port": 1, "dst_block": "C", "dst_port": 1}
]}
```

#### Failure strategy: Stop and report

Processing stops at the first failure. Response includes all successful results plus the error.

**All succeed:**
```json
{
  "action": "block_add",
  "completed": 3,
  "total": 3,
  "results": [
    {"source": "simulink/Gain", "destination": "m/Gain1", "verified": true},
    {"source": "simulink/Sum", "destination": "m/Sum1", "verified": true},
    {"source": "simulink/Mux", "destination": "m/Mux1", "verified": true}
  ]
}
```

**Partial failure:**
```json
{
  "action": "block_add",
  "completed": 2,
  "total": 3,
  "results": [
    {"source": "simulink/Gain", "destination": "m/Gain1", "verified": true},
    {"source": "simulink/Sum", "destination": "m/Sum1", "verified": true}
  ],
  "error": {
    "index": 2,
    "error": "source_not_found",
    "message": "Source block 'bad/path' not found.",
    "item": {"source": "bad/path", "destination": "m/X"}
  }
}
```

#### Rollback

Batch mode does **not** roll back already-completed items on failure. Rationale:
- Each block/line is independently valid
- Rolling back 7 successful blocks because #8 failed is wasteful
- The agent knows exactly which items succeeded (`results`) and can resume from the failure point
- Individual rollback payloads are not included in batch results (would bloat response). The agent can use `block_delete` / `line_delete` if rollback is needed.

#### Validation

- `blocks` array: each item must have `source` (string) and `destination` (string). `position` is optional (4-element numeric array).
- `lines` array: each item must have `src_block`, `src_port`, `dst_block`, `dst_port`.
- Empty array is rejected.
- Maximum array size: 100 items (prevent accidental megabatch).

---

## Implementation Order

1. **FEAT-002b** (simulate stores results) — prerequisite for FEAT-004
2. **FEAT-005** (batch mode) — independent, can parallel with FEAT-004
3. **FEAT-004** (sim-analyst agent) — depends on FEAT-002b

---

## Files Changed (estimated)

| Item | Files |
|------|-------|
| FEAT-002b | `simulink_cli/actions/simulate_cmd.py`, `simulink_cli/matlab_transport.py`, `tests/test_simulate_behavior.py`, `tests/fakes.py` |
| FEAT-004 | `agents/sim-analyst.md`, `.claude-plugin/plugin.json`, `skills/simulink_automation/SKILL.md` |
| FEAT-005 | `simulink_cli/actions/block_cmd.py`, `simulink_cli/actions/line_add.py`, `tests/test_block_cmd_behavior.py`, `tests/test_line_add_behavior.py`, `tests/test_json_input_mode.py` |
| Docs | `skills/simulink_automation/SKILL.md`, `skills/simulink_automation/reference.md` |
| Schema | `tests/test_schema_action.py` (version bump to 2.9) |
