# Roadmap

Status: Active (established 2026-03-21, refined with Phase 1 sub-phase design 2026-03-21)

## Product Goal

Let AI agents perform the standard Simulink modeling workflow: create models, add/remove blocks, connect/disconnect signals, configure parameters, run simulations, and save results. Advanced operations (complex subsystems, tuning loops, etc.) are compositions of these basics — no dedicated high-level actions needed.

Out of scope: Stateflow, Code Generation, Model Reference, Bus Objects, and other non-model-building capabilities.

## Capability Baseline

A normal person building a Simulink model uses these basic operations:

| # | Capability | MATLAB Function | CLI Action | Status |
|---|-----------|----------------|------------|--------|
| 1 | Create new model | `new_system` | `model_new` | TODO (v2.1.0) |
| 2 | Open model | `open_system` | `model_open` | TODO (v2.1.0) |
| 3 | Save model | `save_system` | `model_save` | TODO (v2.1.0) |
| 4 | Close model | `close_system` | `model_close` | TODO (Phase 2) |
| 5 | Update/compile model | `update_diagram` | `model_update` | TODO (Phase 2) |
| 6 | Add block | `add_block` | `block_add` | TODO (v2.2.0) |
| 7 | Delete block | `delete_block` | `block_delete` | TODO (Phase 3) |
| 8 | Connect blocks (point-to-point) | `add_line` | `line_add` | TODO (v2.3.0) |
| 9 | Disconnect blocks (point-to-point) | `delete_line` | `line_delete` | TODO (Phase 2) |
| 10 | Set parameter | `set_param` | `set_param` | Done (v2.0) |
| 11 | Read parameter | `get_param` via inspect | `inspect` | Done (v1.0) |
| 12 | Find blocks | `find_system` via find | `find` | Done (v1.3) |
| 13 | Analyze structure | scan / connections | `scan`, `connections` | Done (v1.0) |
| 14 | Run simulation | `sim` | `simulate` | TODO (Phase 2) |

## Action Design

New operations use **independent flat action names** with noun-prefix grouping. Each action is a separate entry in the `_ACTIONS` registry with its own self-contained schema — no sub-operation field.

This was chosen over the action-family pattern (grouping sub-operations under one action) because:
- AI agents make fewer errors with flat, unambiguous action names
- Each action has a simple, independent schema (no conditional required fields)
- Maps 1:1 to MCP tools if MCP is adopted later

The existing `session` action uses a hybrid pattern (single action with internal `session_action` enum). New actions diverge too much in required fields to reuse that pattern.

| Action | Module | Safety Tier |
|--------|--------|-------------|
| `model_new` | `model_cmd.py` | Checked Mutation |
| `model_open` | `model_cmd.py` | Operational |
| `model_save` | `model_cmd.py` | Operational |
| `model_close` | `model_cmd.py` | Operational (Phase 2) |
| `model_update` | `model_cmd.py` | Operational (Phase 2) |
| `block_add` | `block_cmd.py` | Checked Mutation |
| `block_delete` | `block_cmd.py` | Full Guarded (Phase 3) |
| `line_add` | `line_cmd.py` | Checked Mutation |
| `line_delete` | `line_cmd.py` | Checked Mutation (Phase 2) |
| `simulate` | `simulate.py` | Operational (Phase 2) |

Existing actions unchanged: `scan`, `connections`, `inspect`, `find`, `highlight`, `list_opened`, `set_param`, `session`.

Total after completion: 18 actions (8 existing + 10 new).

## Safety Model Tiers

Not every operation needs the full `set_param`-style ceremony. Three tiers:

### Full Guarded

dry_run default true → apply_payload → precondition check → execute → read-back verify → rollback payload.

Applies to: `set_param`, `block_delete`.

These operations can destroy existing state. Preview and guarded execute are justified.

### Checked Mutation

Precondition check → execute → verify → rollback payload. No dry_run preview ceremony.

Applies to: `block_add`, `line_add`, `line_delete`, `model_new`.

These operations create or remove structure. Precondition and rollback matter, but "previewing an add" adds little value.

### Operational

Execute → error handling → necessary constraints. No dry_run or rollback.

Applies to: `model_open`, `model_save`, `model_close`, `model_update`, `simulate`.

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

Phase 1 is split into 3 independently releasable sub-phases. Each sub-phase gets its own minor version, manifest sync, docs update, and validation cycle.

Design reference: `docs/superpowers/specs/2026-03-21-phase1-sub-phases-design.md`

#### v2.1.0 — Model Lifecycle Management

Goal: AI can create, open, and save Simulink models.

- [ ] `model_new` action (Checked Mutation: precondition + execute + verify + rollback)
- [ ] `model_open` action (Operational: execute + error handling)
- [ ] `model_save` action (Operational: execute + error handling; native overwrite semantics)
- [ ] New module: `simulink_cli/actions/model_cmd.py`
- [ ] Register in `simulink_cli/core.py` (`_ACTIONS`, FIELDS, schema) and `actions/__init__.py`
- [ ] Transport wrappers: `new_system()`, `open_system()`, `save_system()`
- [ ] Fake engine extensions for model lifecycle
- [ ] `test_model_cmd_behavior.py` — behavior tests with mocked MATLAB
- [ ] Schema contract updated
- [ ] Error codes: reuse existing + `model_already_loaded`, `model_save_failed` as needed
- [ ] SKILL.md, reference.md, test-scenarios.md updated
- [ ] README.md, README.zh-CN.md updated
- [ ] Docs contract tests updated
- [ ] Version bump: plugin.json, marketplace.json → 2.1.0; schema version → 2.1
- [ ] Full validation: tests + manifest check + `claude plugin validate .`

#### v2.2.0 — Block Placement

Goal: AI can add blocks to a model.

- [ ] `block_add` action (Checked Mutation: precondition + execute + verify + deferred rollback)
- [ ] New module: `simulink_cli/actions/block_cmd.py`
- [ ] Register in `simulink_cli/core.py` and `actions/__init__.py`
- [ ] Transport wrapper: `add_block()`
- [ ] Fake engine extension for block operations
- [ ] `test_block_cmd_behavior.py` — behavior tests
- [ ] Schema contract updated
- [ ] Error codes: `source_not_found`, `block_already_exists` as needed
- [ ] SKILL.md, reference.md, test-scenarios.md updated
- [ ] README.md, README.zh-CN.md updated
- [ ] Docs contract tests updated
- [ ] Version bump → 2.2.0; schema version → 2.2
- [ ] Full validation

#### v2.3.0 — Signal Routing + End-to-End Workflow

Goal: AI can connect block ports, completing the first full modeling workflow.

- [ ] `line_add` action (Checked Mutation: precondition + execute + verify + deferred rollback)
- [ ] New module: `simulink_cli/actions/line_cmd.py`
- [ ] Register in `simulink_cli/core.py` and `actions/__init__.py`
- [ ] Transport wrapper: `add_line()`
- [ ] Fake engine extension for line operations
- [ ] `test_line_cmd_behavior.py` — behavior tests
- [ ] **End-to-end workflow test:** `model_new` → `block_add` (x2+) → `line_add` → `set_param` → `model_save`
- [ ] Live MATLAB smoke test script (covers full creation workflow)
- [ ] Schema contract updated
- [ ] Error codes: `port_not_found`, `line_already_exists` as needed
- [ ] SKILL.md, reference.md, test-scenarios.md updated
- [ ] README.md, README.zh-CN.md updated
- [ ] Docs contract tests updated
- [ ] Version bump → 2.3.0; schema version → 2.3
- [ ] Full validation

### Phase 2 — Iterate and Verify

Goal: AI can modify an existing model, remove connections, run simulations, and verify results.

- [ ] `line_delete` action (Checked Mutation)
- [ ] `simulate` action (Operational)
- [ ] `model_close` action (Operational, with dirty-state check)
- [ ] `model_update` action (Operational)
- [ ] Transport wrappers: `delete_line()`, `sim()`, `close_system()`, `update_diagram()`
- [ ] Tests: iterate workflow (model_open → set_param → simulate → inspect → model_save → model_close)
- [ ] Live smoke coverage for simulation flow
- [ ] Activate deferred rollback for `line_add` (now that `line_delete` exists)
- [ ] SKILL.md and docs update
- [ ] Release

### Phase 3 — Safe Destructive Topology Edits

Goal: AI can safely remove blocks with state capture for rollback.

- [ ] `block_delete` action (Full Guarded: dry_run + capture params/connections + execute + verify + rollback)
- [ ] Transport wrapper: `delete_block()`
- [ ] Rollback design: decide full restore vs limited restore (library default + manual re-config)
- [ ] Tests: delete → rollback → verify restored state
- [ ] Activate deferred rollback for `block_add` (now that `block_delete` exists)
- [ ] Live smoke coverage for destructive edit flow
- [ ] SKILL.md and docs update
- [ ] Release

### Post-Phase 3 — Driven by Real Usage

These are not planned but may become relevant based on actual usage:

- [ ] `replace_block` (swap block type preserving connections)
- [ ] Branched signal line support (non-point-to-point connections)
- [ ] Batch / multi-operation workflows (transaction-like semantics)
- [ ] Token efficiency benchmark: CLI compact mode vs thin MCP wrapper (evaluation only, owner-driven timing)
- [ ] MCP as primary exposure layer (if benchmark justifies and demand exists)

## MCP Evaluation Strategy

MCP is not pre-committed but no longer dismissed. Evaluation timing is owner-driven — not bound to any specific phase milestone.

When evaluation happens:

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
