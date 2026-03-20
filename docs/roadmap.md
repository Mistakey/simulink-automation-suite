# Roadmap

Status: Draft (established via dual-AI architecture review, 2026-03-21)

## Product Goal

Let AI agents perform the standard Simulink modeling workflow: create models, add/remove blocks, connect/disconnect signals, configure parameters, run simulations, and save results. Advanced operations (complex subsystems, tuning loops, etc.) are compositions of these basics — no dedicated high-level actions needed.

Out of scope: Stateflow, Code Generation, Model Reference, Bus Objects, and other non-model-building capabilities.

## Capability Baseline

A normal person building a Simulink model uses these basic operations:

| # | Capability | MATLAB Function | Status |
|---|-----------|----------------|--------|
| 1 | Create new model | `new_system` | TODO |
| 2 | Open model | `open_system` | TODO |
| 3 | Save model | `save_system` | TODO |
| 4 | Close model | `close_system` | TODO |
| 5 | Update/compile model | `update_diagram` | TODO |
| 6 | Add block | `add_block` | TODO |
| 7 | Delete block | `delete_block` | TODO |
| 8 | Connect blocks (point-to-point) | `add_line` | TODO |
| 9 | Disconnect blocks (point-to-point) | `delete_line` | TODO |
| 10 | Set parameter | `set_param` | Done (v2.0) |
| 11 | Read parameter | `get_param` via inspect | Done (v1.0) |
| 12 | Find blocks | `find_system` via find | Done (v1.3) |
| 13 | Analyze structure | scan / connections | Done (v1.0) |
| 14 | Run simulation | `sim` | TODO |

## Action Family Design

New operations are grouped into compact action families (precedent: `session list/use/current/clear` in one module). This keeps the action registry tight instead of adding one top-level action per MATLAB function.

| Action | Sub-operations | New Module |
|--------|---------------|------------|
| `model` | `new`, `open`, `save`, `close`, `update` | `simulink_cli/actions/model_cmd.py` |
| `block` | `add`, `delete` | `simulink_cli/actions/block_cmd.py` |
| `line` | `add`, `delete` (point-to-point; branched signals deferred) | `simulink_cli/actions/line_cmd.py` |
| `simulate` | (single operation) | `simulink_cli/actions/simulate.py` |

Existing actions unchanged: `scan`, `connections`, `inspect`, `find`, `highlight`, `list_opened`, `set_param`, `session`.

Total after completion: 12 actions (8 existing + 4 new).

## Safety Model Tiers

Not every operation needs the full `set_param`-style ceremony. Three tiers:

### Full Guarded

dry_run default true → apply_payload → precondition check → execute → read-back verify → rollback payload.

Applies to: `set_param`, `block delete`.

These operations can destroy existing state. Preview and guarded execute are justified.

### Checked Mutation

Precondition check → execute → verify → rollback payload. No dry_run preview ceremony.

Applies to: `block add`, `line add`, `line delete`, `model new`.

These operations create or remove structure. Precondition and rollback matter, but "previewing an add" adds little value.

### Operational

Execute → error handling → necessary constraints. No dry_run or rollback.

Applies to: `model open`, `model save`, `model close`, `model update`, `simulate`.

Constraints still apply: `close` must check dirty state before discarding, `save` must handle overwrite semantics. But these are not mutation-preview operations.

## Transport Layer

`matlab_transport.py` already has generic `call()` and `call_no_output()` wrappers. New operations are one-liner additions:

```python
def add_block(engine, source, dest):
    return call_no_output(engine, "add_block", source, dest)

def delete_block(engine, block_path):
    return call_no_output(engine, "delete_block", block_path)

def add_line(engine, system, src, dst):
    return call(engine, "add_line", system, src, dst)

def delete_line(engine, system, src, dst):
    return call_no_output(engine, "delete_line", system, src, dst)

def new_system(engine, name):
    return call(engine, "new_system", name)

def save_system(engine, model):
    return call_no_output(engine, "save_system", model)

def open_system(engine, path):
    return call_no_output(engine, "open_system", path)

def close_system(engine, model):
    return call_no_output(engine, "close_system", model)

def update_diagram(engine, model):
    # Actual implementation TBD; likely via set_param(model, 'SimulationCommand', 'update')
    return call_no_output(engine, "set_param", model, "SimulationCommand", "update")

def sim(engine, model):
    return call(engine, "sim", model)
```

## Phased Delivery

Phases are ordered by "AI can complete an end-to-end workflow", not by single-operation complexity.

### Phase 1 — From Zero to a Saveable Model

Goal: AI can create a new model, add blocks, connect them, set parameters, and save.

- [ ] `model` action: `new` sub-operation
- [ ] `model` action: `open` sub-operation
- [ ] `model` action: `save` sub-operation
- [ ] `block` action: `add` sub-operation
- [ ] `line` action: `add` sub-operation
- [ ] Transport wrappers: `new_system`, `open_system`, `save_system`, `add_block`, `add_line`
- [ ] Fake engines for new action families
- [ ] Tests: contract, behavior, workflow (create → add block → connect → set_param → save)
- [ ] Live MATLAB smoke test script (covers set_param + new ops)
- [ ] SKILL.md and docs update for new actions
- [ ] Token efficiency benchmark: CLI compact mode vs thin MCP wrapper (evaluation only)
- [ ] Schema version bump (major.minor per release rules)
- [ ] Release: version bump, manifest sync, validation

### Phase 2 — Iterate and Verify

Goal: AI can modify an existing model, remove connections, run simulations, and verify results.

- [ ] `line` action: `delete` sub-operation
- [ ] `simulate` action
- [ ] `model` action: `close` sub-operation (with dirty-state check)
- [ ] `model` action: `update` sub-operation
- [ ] Transport wrappers: `delete_line`, `sim`, `close_system`, `update_diagram`
- [ ] Tests: iterate workflow (open → modify → simulate → verify → save → close)
- [ ] Live smoke coverage for simulation flow
- [ ] If Phase 1 benchmark favors MCP: implement thin MCP adapter layer
- [ ] SKILL.md and docs update
- [ ] Release

### Phase 3 — Safe Destructive Topology Edits

Goal: AI can safely remove blocks with state capture for rollback.

- [ ] `block` action: `delete` sub-operation (full guarded: capture params + connections at dry_run)
- [ ] Transport wrapper: `delete_block`
- [ ] Rollback design: decide full restore vs limited restore (library default + manual re-config)
- [ ] Tests: delete → rollback → verify restored state
- [ ] Live smoke coverage for destructive edit flow
- [ ] SKILL.md and docs update
- [ ] Release

### Post-Phase 3 — Driven by Real Usage

These are not planned but may become relevant based on actual usage:

- [ ] `replace_block` (swap block type preserving connections)
- [ ] Branched signal line support (non-point-to-point connections)
- [ ] Batch / multi-operation workflows (transaction-like semantics)
- [ ] MCP as primary exposure layer (if benchmark justifies and demand exists)

## MCP Evaluation Strategy

MCP is not pre-committed but no longer dismissed. Evaluation happens during Phase 1:

1. Pick a representative task (e.g., "create model, add 3 blocks, connect them, set params, save")
2. Measure: tool-call count, request/response size, context window consumption
3. Compare: current CLI + SKILL.md vs compact CLI vs thin MCP wrapper
4. Decision criteria: if MCP shows measurably lower token cost for equivalent safety, adopt as supplementary exposure layer. Core logic stays in `simulink_cli`.

## What This Roadmap Does NOT Cover

- Stateflow editing
- Code Generation configuration
- Model Reference management
- Bus Objects
- Variant Subsystems
- Timeline or date commitments
- Plugin rename (name stays `simulink-automation-suite`)

## Origin

This roadmap was established through a structured dual-AI architecture review on 2026-03-21. The review examined all core source files, tests, design documents, and release history, then went through multiple rounds of debate with direct project-owner feedback correcting two critical misjudgments:

1. Initial consensus wrongly deprioritized structural editing. Owner pointed out that without write capability, the tool has no meaningful value over ad-hoc scanning.
2. Initial consensus ignored token efficiency and MCP evaluation. Owner pointed out that the current architecture's per-operation overhead may not scale to 13+ operations.
