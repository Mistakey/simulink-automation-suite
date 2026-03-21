# Phase 1 Sub-Phases Design: Independent Actions and Staged Delivery

**Date:** 2026-03-21
**Status:** Reviewed (post spec-review round 1)
**Plugin:** simulink-automation-suite
**Baseline:** v2.0.3 (8 actions, unified simulink_cli/ package)

---

## Context

The roadmap (`docs/roadmap.md`, established 2026-03-21) defines Phase 1 as "From Zero to a Saveable Model" — the first milestone where an AI agent can create a model, add blocks, connect signals, set parameters, and save. This design specifies how Phase 1 is decomposed into independently releasable sub-phases, and documents two key design decisions that revise the original roadmap.

## Decision 1: Independent Actions Over Action Families

### Original Design

The roadmap grouped new operations into action families with a sub-operation field:

```json
{"action": "model", "operation": "new", "name": "my_model"}
```

### Revised Design

Use flat, independent action names with noun-prefix grouping:

```json
{"action": "model_new", "name": "my_model"}
```

### Rationale

Evaluated from the AI agent's perspective:

| Dimension | Family | Independent | Winner |
|-----------|--------|-------------|--------|
| Tool selection | 2-step: pick action + pick operation | 1-step: pick action | Independent |
| Schema complexity | Conditional fields per operation | Flat, self-contained schema | Independent |
| Hallucination risk | Agent can invent wrong operation names | Action name IS the operation | Independent |
| MCP alignment | Requires splitting or complex tool | 1:1 mapping to MCP tool | Independent |
| Registry size | ~12 actions | ~18 actions | Family (marginal) |

The registry size difference (~18 vs ~12) is negligible for agent tool selection. The clarity and simplicity advantages of independent actions decisively outweigh the grouping benefit.

### Naming Convention

Existing multi-word actions use underscores: `set_param`, `list_opened`. New actions follow **noun_verb** prefix grouping:

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

Noun prefix ensures related operations sort together in schema output, aiding agent discoverability.

### Relationship to Existing `session` Action

The existing `session` action uses a hybrid pattern: it is a single registered action with an internal `session_action` enum field (`list`/`use`/`current`/`clear`). This works for `session` because its sub-operations share a nearly identical field set. New actions diverge significantly in their required fields (e.g., `model_new` needs `name`, `model_open` needs `path`), making the hybrid pattern a poor fit. New actions use fully independent registry entries instead.

### Code Organization

API surface is flat, but module organization still groups by family:

```
simulink_cli/actions/
  model_cmd.py      # model_new, model_open, model_save (v2.1.0)
                    # + model_close, model_update (Phase 2)
  block_cmd.py      # block_add (v2.2.0), block_delete (Phase 3)
  line_cmd.py       # line_add (v2.3.0), line_delete (Phase 2)
  simulate.py       # simulate (Phase 2)
```

## Decision 2: Token Efficiency Benchmark Deferred

### Original Design

The roadmap included "Token efficiency benchmark: CLI compact mode vs thin MCP wrapper" as a Phase 1 deliverable.

### Revised Design

Removed from Phase 1 fixed deliverables. Owner evaluates timing independently based on usage needs.

### Impact on MCP Evaluation Strategy

The roadmap's MCP Evaluation Strategy section no longer binds to Phase 1 timeline. MCP evaluation happens when the owner determines it is needed, not at a predetermined milestone.

## Decision 3: Phase 1 Split Into 3 Sub-Phases

### Delivery Strategy

Each sub-phase is an independent minor release with full version bump, manifest sync, docs update, and validation.

### v2.1.0 — Model Lifecycle Management

**Goal:** AI can create, open, and save Simulink models.

**New actions:**

| Action | Required Fields | Optional Fields | Safety Tier |
|--------|----------------|-----------------|-------------|
| `model_new` | `name` | `session` | Checked Mutation |
| `model_open` | `path` | `session` | Operational |
| `model_save` | `model` | `session` | Operational |

**Safety model:**
- `model_new`: precondition check (model name not already loaded) + execute + verify (model exists) + rollback payload (`close_system` without save)
- `model_open`: execute + error handling (file not found, already open)
- `model_save`: execute + error handling (model not loaded, save failure). Note: `save_system` overwrites the existing `.slx` file. For v2.1.0 this is intentional (matches MATLAB's native behavior). Overwrite-warning or backup semantics are deferred unless usage reveals a need.

**Deliverables:**
- [ ] `simulink_cli/actions/model_cmd.py` — action implementation
- [ ] Register new actions in `simulink_cli/core.py` (`_ACTIONS`, FIELDS, schema) and `simulink_cli/actions/__init__.py`
- [ ] Transport wrappers: `new_system()`, `open_system()`, `save_system()`
- [ ] Fake engine extensions for model lifecycle
- [ ] `test_model_cmd_behavior.py` — behavior tests with mocked MATLAB
- [ ] Schema contract updated (`model_new`, `model_open`, `model_save` in schema output)
- [ ] Error codes: reuse existing + `model_already_loaded`, `model_save_failed` as needed
- [ ] SKILL.md, reference.md, test-scenarios.md updated
- [ ] README.md, README.zh-CN.md updated
- [ ] Docs contract tests updated
- [ ] Version bump: plugin.json, marketplace.json → 2.1.0; schema version → 2.1
- [ ] Full validation: tests + manifest check + `claude plugin validate .`

### v2.2.0 — Block Placement

**Goal:** AI can add blocks to a model.

**New action:**

| Action | Required Fields | Optional Fields | Safety Tier |
|--------|----------------|-----------------|-------------|
| `block_add` | `model`, `source`, `dest` | `session` | Checked Mutation |

`source` is the Simulink library path (e.g., `simulink/Math Operations/Gain`).
`dest` is the target path in the model (e.g., `my_model/Gain1`).

**Safety model:**
- Precondition check: model is loaded, source block exists in library
- Execute: `add_block(source, dest)`
- Verify: block exists at dest path via `get_param(dest, 'Handle')`
- Rollback: `block_delete` does not exist until roadmap Phase 3. At v2.2.0, the response includes a `rollback` field with `{"action": "block_delete", "target": "<dest>", "available": false, "note": "block_delete not yet implemented; use MATLAB delete_block manually to undo"}`. This gives agents the rollback shape for future use while clearly signaling it is not yet executable.

**Deliverables:**
- [ ] `simulink_cli/actions/block_cmd.py` — action implementation
- [ ] Register in `simulink_cli/core.py` and `simulink_cli/actions/__init__.py`
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

### v2.3.0 — Signal Routing + End-to-End Workflow

**Goal:** AI can connect block ports, completing the first full modeling workflow.

**New action:**

| Action | Required Fields | Optional Fields | Safety Tier |
|--------|----------------|-----------------|-------------|
| `line_add` | `system`, `src_port`, `dst_port` | `session` | Checked Mutation |

`system` is the parent system/subsystem path.
`src_port` is `<block_name>/<port_number>` (e.g., `Gain1/1`).
`dst_port` is `<block_name>/<port_number>` (e.g., `Scope1/1`).

**Safety model:**
- Precondition check: system loaded, source and destination ports exist
- Execute: `add_line(system, src_port, dst_port)`
- Verify: line handle returned and valid
- Rollback: `line_delete` does not exist until roadmap Phase 2 (which follows all Phase 1 sub-phases). At v2.3.0, the response includes a `rollback` field with `{"action": "line_delete", "system": "<system>", "src_port": "<src>", "dst_port": "<dst>", "available": false, "note": "line_delete not yet implemented; use MATLAB delete_line manually to undo"}`. Same pattern as `block_add`'s deferred rollback.

**Deliverables:**
- [ ] `simulink_cli/actions/line_cmd.py` — action implementation
- [ ] Register in `simulink_cli/core.py` and `simulink_cli/actions/__init__.py`
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

## Roadmap File Changes

The following sections in `docs/roadmap.md` require updates:

| Section | Change |
|---------|--------|
| Action Family Design | Replace family/sub-operation design with independent action table |
| Phase 1 | Split into 3 sub-phases (v2.1.0, v2.2.0, v2.3.0) with individual checklists |
| Phase 1 checklist | Remove "Token efficiency benchmark" line item |
| MCP Evaluation Strategy | Decouple from Phase 1 timeline; mark as owner-driven |
| Transport Layer | No changes needed — transport wrapper function names (`new_system`, `add_block`, etc.) are MATLAB-level names unaffected by the action naming decision |

Sections unchanged: Product Goal, Capability Baseline (update action names only), Safety Model Tiers, Phase 2, Phase 3, Post-Phase 3, What This Roadmap Does NOT Cover, Origin.

## Validation Checklist

Before concluding this design work:

- [ ] Design doc written and committed
- [ ] `docs/roadmap.md` updated to reflect all decisions
- [ ] No contradictions between roadmap and this design doc
- [ ] Action names consistent across all documents
