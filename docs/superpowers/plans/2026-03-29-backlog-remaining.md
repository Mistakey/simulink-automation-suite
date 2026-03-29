# Backlog Remaining Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement three remaining backlog items: simulate stores results in workspace (FEAT-002b), sim-analyst subagent (FEAT-004), and batch mode for block_add/line_add (FEAT-005).

**Architecture:** FEAT-002b switches simulate to use evalc-based execution so the SimulationOutput object stays in the MATLAB workspace. FEAT-004 is a new agent markdown file plus registration. FEAT-005 extends existing block_add/line_add with a mutually-exclusive array field that loops through items with stop-on-first-failure semantics.

**Tech Stack:** Python 3, unittest, simulink_cli action module pattern, Claude Code agent markdown format.

**Spec:** `docs/superpowers/specs/2026-03-29-backlog-remaining-design.md`

**Branch:** `fix/backlog-quick-wins` (continue existing work)

**Test runner:** `python -m unittest <module> -v`

---

## File Map

| File | Role | Task |
|------|------|------|
| `simulink_cli/actions/simulate_cmd.py` | Switch to evalc-based sim with workspace storage | 1 |
| `tests/test_simulate_behavior.py` | Tests for workspace storage | 1 |
| `tests/fakes.py` | Add evalc sim pattern to FakeModelEngine | 1 |
| `skills/simulink_automation/SKILL.md` | Document sl_sim_result, sim-analyst handoff | 2, 3 |
| `agents/sim-analyst.md` | New agent definition | 3 |
| `.claude-plugin/plugin.json` | Register sim-analyst agent | 3 |
| `simulink_cli/actions/block_cmd.py` | Add blocks batch field, validate, execute | 4, 5 |
| `tests/test_block_cmd_behavior.py` | Batch block_add tests | 4, 5 |
| `simulink_cli/actions/line_add.py` | Add lines batch field, validate, execute | 6, 7 |
| `tests/test_line_add_behavior.py` | Batch line_add tests | 6, 7 |
| `tests/test_json_input_mode.py` | JSON parsing tests for batch fields | 5, 7 |
| `simulink_cli/core.py` | Schema version bump to 2.9 | 8 |
| `tests/test_schema_action.py` | Version assertion update | 8 |

---

### Task 1: FEAT-002b -- simulate stores results in workspace

**Files:**
- Modify: `tests/fakes.py` -- extend FakeModelEngine.evalc for sim pattern
- Modify: `tests/test_simulate_behavior.py` -- add workspace storage test
- Modify: `simulink_cli/actions/simulate_cmd.py` -- switch to evalc-based simulation

- [ ] **Step 1: Update FakeModelEngine to support evalc sim pattern**

In `tests/fakes.py`, add `self._workspace = {}` to `FakeModelEngine.__init__` (after `self._update_output = update_output`).

Replace the existing `evalc` method with:

```python
    def evalc(self, code, nargout=1, background=False):
        import re
        if "SimulationCommand" in code and "update" in code:
            match = re.search(r"'(\w+)'", code)
            if match:
                model = match.group(1)
                self.set_param(model, "SimulationCommand", "update", nargout=0)
            return self._update_output
        if "sl_sim_result = sim(" in code:
            match = re.search(r"sim\('(\w+)'", code)
            if match:
                model = match.group(1)
                if model not in self._loaded:
                    raise RuntimeError(f"Model '{model}' is not loaded")
            self._workspace["sl_sim_result"] = "sim_output"
            return ""
        raise RuntimeError(f"Unsupported evalc: {code}")
```

- [ ] **Step 2: Write failing test for workspace storage**

In `tests/test_simulate_behavior.py`, add to `SimulateExecuteTests`:

```python
    def test_simulate_stores_result_in_workspace(self):
        eng = FakeModelEngine(loaded_models=["m"])
        result = self._run(self._default_args(), engine=eng)
        self.assertNotIn("error", result)
        self.assertIn("sl_sim_result", eng._workspace)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m unittest tests.test_simulate_behavior.SimulateExecuteTests.test_simulate_stores_result_in_workspace -v`
Expected: FAIL -- `_workspace` attribute missing or `sl_sim_result` not stored.

- [ ] **Step 4: Implement evalc-based simulation in simulate_cmd.py**

Replace the simulation execution block in `simulink_cli/actions/simulate_cmd.py` (lines 103-135, from `# Execute simulation` through the final `except` block) with:

```python
    # Execute simulation via evalc (stores result in workspace)
    sim_params = {}
    sim_args = [f"'{model}'"]
    if args.get("stop_time") is not None:
        sim_params["StopTime"] = args["stop_time"]
        sim_args.append(f"'StopTime', '{args['stop_time']}'")
    if args.get("max_step") is not None:
        sim_params["MaxStep"] = args["max_step"]
        sim_args.append(f"'MaxStep', '{args['max_step']}'")

    sim_code = f"sl_sim_result = sim({', '.join(sim_args)}); assignin('base', 'sl_sim_result', sl_sim_result);"

    timeout = args.get("timeout")
    effective_timeout = timeout if timeout is not None else 120

    try:
        result = matlab_transport.eval_code(eng, sim_code, timeout=effective_timeout)
        warnings = result.get("warnings", [])
    except TimeoutError:
        return make_error(
            "simulation_timeout",
            f"Simulation timed out after {timeout}s for model '{model}'.",
            details={"model": model, "timeout": timeout},
            suggested_fix="Increase timeout, reduce StopTime, or increase MaxStep to speed up simulation.",
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "simulation" in msg or "solver" in msg or "algebraic" in msg:
            return make_error(
                "simulation_failed",
                f"Simulation failed for model '{model}': {exc}",
                details={"model": model, "cause": str(exc)},
                suggested_fix="Check model for errors (algebraic loops, solver mismatches, unconnected ports).",
            )
        return make_error(
            "runtime_error",
            f"Unexpected error simulating model '{model}': {exc}",
            details={"model": model, "cause": str(exc)},
        )
```

- [ ] **Step 5: Run all simulate tests**

Run: `python -m unittest tests.test_simulate_behavior -v`
Expected: All PASS including the new workspace storage test. Some existing tests may need `_default_args` to include `stop_time` and `max_step` defaults -- fix as needed.

- [ ] **Step 6: Commit**

```bash
git add simulink_cli/actions/simulate_cmd.py tests/test_simulate_behavior.py tests/fakes.py
git commit -m "feat(FEAT-002b): simulate stores result in workspace sl_sim_result"
```

---

### Task 2: FEAT-002b -- Document sl_sim_result in SKILL.md

**Files:**
- Modify: `skills/simulink_automation/SKILL.md`

- [ ] **Step 1: Add simulation results access pattern to Common Patterns**

In `skills/simulink_automation/SKILL.md`, after the "Multi-line MATLAB code via matlab_eval" section, add:

```markdown
### Access simulation results

After `simulate` runs, the `SimulationOutput` object is stored in the base workspace as `sl_sim_result`. Use `matlab_eval` to query it:

```json
{"action": "matlab_eval", "code": "signals = sl_sim_result.logsout.getElementNames; for i=1:numel(signals), fprintf('%s\\n', signals{i}); end"}
```

For detailed waveform analysis, dispatch the `sim-analyst` agent (see Responsibility & Handoff).
```

- [ ] **Step 2: Run docs contract tests**

Run: `python -m unittest tests.test_docs_contract -v`
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add skills/simulink_automation/SKILL.md
git commit -m "docs(FEAT-002b): document sl_sim_result workspace variable"
```

---

### Task 3: FEAT-004 -- sim-analyst agent

**Files:**
- Create: `agents/sim-analyst.md`
- Modify: `.claude-plugin/plugin.json`
- Modify: `skills/simulink_automation/SKILL.md`

- [ ] **Step 1: Create the agent definition**

Create `agents/sim-analyst.md` with the full agent prompt. Key elements:
- Frontmatter: name=sim-analyst, model=sonnet, color=green, tools=[Bash, Write, Read, Grep, Glob]
- Description: post-simulation data analysis
- Read-only constraint: never execute set_param, simulate, model_new, etc.
- Data source: `sl_sim_result` workspace variable
- Analysis strategies: matlab_eval for quick checks, Python scripts for complex analysis
- CLI invocation pattern
- 6-section output envelope (Context, Answer, Evidence, Actions Performed, Limitations, Suggested Followup)

(Full content in spec section 2.)

- [ ] **Step 2: Register in plugin.json**

In `.claude-plugin/plugin.json`, change:

```json
  "agents": [
    "./agents/simulink-analyzer.md"
  ],
```

to:

```json
  "agents": [
    "./agents/simulink-analyzer.md",
    "./agents/sim-analyst.md"
  ],
```

- [ ] **Step 3: Add sim-analyst to SKILL.md Responsibility & Handoff**

In `skills/simulink_automation/SKILL.md`, after the "Delegate to simulink-analyzer agent" section, add:

```markdown
### Delegate to sim-analyst agent

| Action | Reason |
|--------|--------|
| Post-simulation signal analysis | Waveform data can be millions of points; isolate from main context |
| Dynamic performance evaluation | Rise time, overshoot, settling time, steady-state error |
| Multi-signal comparison | Cross-correlation, phase analysis |

Before dispatching, ensure `simulate` has been run (so `sl_sim_result` exists in workspace). Provide session, model, and specific analysis goals.
```

- [ ] **Step 4: Run docs contract and agent definition tests**

Run: `python -m unittest tests.test_docs_contract tests.test_agent_definition_contract -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/sim-analyst.md .claude-plugin/plugin.json skills/simulink_automation/SKILL.md
git commit -m "feat(FEAT-004): add sim-analyst subagent for post-simulation analysis"
```

---

### Task 4: FEAT-005 -- block_add batch validation

**Files:**
- Modify: `simulink_cli/actions/block_cmd.py` -- add blocks field, refactor validate
- Modify: `tests/test_block_cmd_behavior.py` -- batch validation tests

- [ ] **Step 1: Write failing tests for batch validation**

In `tests/test_block_cmd_behavior.py`, add class `BlockAddBatchValidationTests` with tests for:
- `blocks` + `source`/`destination` mutual exclusion -> `invalid_input`
- Empty `blocks` array -> `invalid_input`
- Item missing `source` -> `invalid_input`
- Item missing `destination` -> `invalid_input`
- Array exceeds 100 items -> `invalid_input`
- Valid blocks array -> None

```python
class BlockAddBatchValidationTests(unittest.TestCase):
    def test_blocks_and_source_mutually_exclusive(self):
        result = block_cmd.validate({
            "source": "simulink/Gain", "destination": "m/G1",
            "blocks": [{"source": "simulink/Gain", "destination": "m/G1"}],
        })
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_empty_blocks_array_rejected(self):
        result = block_cmd.validate({"blocks": [], "session": None,
            "source": None, "destination": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_blocks_item_missing_source_rejected(self):
        result = block_cmd.validate({"blocks": [{"destination": "m/G1"}],
            "session": None, "source": None, "destination": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_blocks_item_missing_destination_rejected(self):
        result = block_cmd.validate({"blocks": [{"source": "simulink/Gain"}],
            "session": None, "source": None, "destination": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_blocks_exceeds_max_size_rejected(self):
        items = [{"source": "simulink/Gain", "destination": f"m/G{i}"} for i in range(101)]
        result = block_cmd.validate({"blocks": items, "session": None,
            "source": None, "destination": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_blocks_returns_none(self):
        result = block_cmd.validate({
            "blocks": [
                {"source": "simulink/Gain", "destination": "m/G1"},
                {"source": "simulink/Sum", "destination": "m/S1"},
            ],
            "session": None, "source": None, "destination": None,
        })
        self.assertIsNone(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_block_cmd_behavior.BlockAddBatchValidationTests -v`
Expected: FAIL.

- [ ] **Step 3: Add blocks field to FIELDS and refactor validate**

In `simulink_cli/actions/block_cmd.py`:

Add `blocks` to FIELDS dict (after `auto_layout`):
```python
    "blocks": {
        "type": "array",
        "required": False,
        "default": None,
        "description": "Batch mode: array of {source, destination, position?} objects. Mutually exclusive with source/destination.",
    },
```

Refactor `validate()` into: `validate()` (dispatch) + `_validate_single()` + `_validate_batch()`. The single validation is the existing logic. Batch validation checks: non-empty, max 100, each item has source (string) and destination (string), optional position (4-element numeric array).

- [ ] **Step 4: Run all block_add tests**

Run: `python -m unittest tests.test_block_cmd_behavior -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add simulink_cli/actions/block_cmd.py tests/test_block_cmd_behavior.py
git commit -m "feat(FEAT-005): block_add batch validation"
```

---

### Task 5: FEAT-005 -- block_add batch execute

**Files:**
- Modify: `simulink_cli/actions/block_cmd.py` -- batch execute logic
- Modify: `tests/test_block_cmd_behavior.py` -- batch execute tests
- Modify: `tests/test_json_input_mode.py` -- JSON parsing test

- [ ] **Step 1: Write failing tests for batch execute**

In `tests/test_block_cmd_behavior.py`, add class `BlockAddBatchExecuteTests` with tests for:
- Batch all succeed: completed==total, results array, no error
- Batch stops on failure: completed < total, error with index/code/item
- Batch model not loaded: completed=0, error

```python
class BlockAddBatchExecuteTests(unittest.TestCase):
    def _make_engine(self, **kwargs):
        defaults = {"loaded_models": ["m"],
            "library_sources": ["simulink/Gain", "simulink/Sum", "simulink/Mux"]}
        defaults.update(kwargs)
        return FakeBlockEngine(**defaults)

    def _run(self, args, engine=None):
        if engine is None:
            engine = self._make_engine()
        with patch.object(block_cmd, "safe_connect_to_session", return_value=(engine, None)):
            return block_cmd.execute(args)

    def test_batch_all_succeed(self):
        result = self._run({"blocks": [
            {"source": "simulink/Gain", "destination": "m/G1"},
            {"source": "simulink/Sum", "destination": "m/S1"},
        ], "session": None, "source": None, "destination": None,
            "position": None, "auto_layout": False})
        self.assertNotIn("error", result)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["total"], 2)
        self.assertTrue(result["results"][0]["verified"])

    def test_batch_stops_on_failure(self):
        result = self._run({"blocks": [
            {"source": "simulink/Gain", "destination": "m/G1"},
            {"source": "bad/path", "destination": "m/X"},
            {"source": "simulink/Sum", "destination": "m/S1"},
        ], "session": None, "source": None, "destination": None,
            "position": None, "auto_layout": False})
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["total"], 3)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["index"], 1)

    def test_batch_model_not_loaded(self):
        eng = self._make_engine(loaded_models=[])
        result = self._run({"blocks": [
            {"source": "simulink/Gain", "destination": "m/G1"},
        ], "session": None, "source": None, "destination": None,
            "position": None, "auto_layout": False}, engine=eng)
        self.assertEqual(result["completed"], 0)
        self.assertIn("error", result)
```

- [ ] **Step 2: Implement batch execute**

In `block_cmd.py`, rename existing `execute()` body to `_execute_single()`, add dispatch in `execute()`:

```python
def execute(args):
    if args.get("blocks") is not None:
        return _execute_batch(args)
    return _execute_single(args)
```

`_execute_batch()`: connect to session, derive model from first item's destination, check model loaded, loop items calling `_execute_single()` per item, stop on first error, return aggregate {action, completed, total, results, error?}.

- [ ] **Step 3: Run batch execute tests**

Run: `python -m unittest tests.test_block_cmd_behavior.BlockAddBatchExecuteTests -v`
Expected: All PASS.

- [ ] **Step 4: Add JSON parsing test**

In `tests/test_json_input_mode.py`:
```python
    def test_parse_json_block_add_batch(self):
        action, args = parse_json_request(
            '{"action":"block_add","blocks":[{"source":"simulink/Gain","destination":"m/G1"}]}')
        self.assertEqual(action, "block_add")
        self.assertIsInstance(args["blocks"], list)
        self.assertIsNone(args["source"])
```

- [ ] **Step 5: Run all block_add and JSON tests**

Run: `python -m unittest tests.test_block_cmd_behavior tests.test_json_input_mode -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add simulink_cli/actions/block_cmd.py tests/test_block_cmd_behavior.py tests/test_json_input_mode.py
git commit -m "feat(FEAT-005): block_add batch execute with stop-on-failure"
```

---

### Task 6: FEAT-005 -- line_add batch validation

**Files:**
- Modify: `simulink_cli/actions/line_add.py` -- add lines field, refactor validate
- Modify: `tests/test_line_add_behavior.py` -- batch validation tests

- [ ] **Step 1: Write failing tests for batch line validation**

In `tests/test_line_add_behavior.py`, add class `LineAddBatchValidationTests` with tests for:
- `lines` + single fields mutual exclusion
- Empty lines array rejected
- Item missing src_block rejected
- Array exceeds 100 items rejected
- Valid lines array returns None

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_line_add_behavior.LineAddBatchValidationTests -v`
Expected: FAIL.

- [ ] **Step 3: Add lines field and refactor validate**

Add `lines` to FIELDS (after `dst_port`):
```python
    "lines": {
        "type": "array",
        "required": False,
        "default": None,
        "description": "Batch mode: array of {src_block, src_port, dst_block, dst_port} objects. Mutually exclusive with individual src_block/src_port/dst_block/dst_port.",
    },
```

Refactor `validate()` into dispatch + `_validate_single_line()` + `_validate_batch_lines()`. Check mutual exclusion between `lines` and any of `src_block/src_port/dst_block/dst_port` being non-None.

- [ ] **Step 4: Run all line_add tests**

Run: `python -m unittest tests.test_line_add_behavior -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add simulink_cli/actions/line_add.py tests/test_line_add_behavior.py
git commit -m "feat(FEAT-005): line_add batch validation"
```

---

### Task 7: FEAT-005 -- line_add batch execute

**Files:**
- Modify: `simulink_cli/actions/line_add.py` -- batch execute logic
- Modify: `tests/test_line_add_behavior.py` -- batch execute tests
- Modify: `tests/test_json_input_mode.py` -- JSON parsing test

- [ ] **Step 1: Write failing tests for batch line execute**

Add class `LineAddBatchExecuteTests` with tests for:
- Batch all succeed: completed==total
- Batch stops on failure (add same line twice, second fails with line_already_exists)
- Batch model not loaded

- [ ] **Step 2: Implement batch execute**

Rename existing `execute()` body to `_execute_single()`, add dispatch + `_execute_batch()`. Same pattern as block_add batch: loop items, delegate to `_execute_single()`, stop on first error, return aggregate.

- [ ] **Step 3: Run batch execute tests**

Run: `python -m unittest tests.test_line_add_behavior.LineAddBatchExecuteTests -v`
Expected: All PASS.

- [ ] **Step 4: Add JSON parsing test**

In `tests/test_json_input_mode.py`:
```python
    def test_parse_json_line_add_batch(self):
        action, args = parse_json_request(
            '{"action":"line_add","model":"m","lines":[{"src_block":"A","src_port":1,"dst_block":"B","dst_port":1}]}')
        self.assertEqual(action, "line_add")
        self.assertIsInstance(args["lines"], list)
        self.assertIsNone(args["src_block"])
```

- [ ] **Step 5: Run all line_add and JSON tests**

Run: `python -m unittest tests.test_line_add_behavior tests.test_json_input_mode -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add simulink_cli/actions/line_add.py tests/test_line_add_behavior.py tests/test_json_input_mode.py
git commit -m "feat(FEAT-005): line_add batch execute with stop-on-failure"
```

---

### Task 8: Final integration -- schema version bump and full test suite

**Files:**
- Modify: `simulink_cli/core.py` -- version "2.8" to "2.9"
- Modify: `tests/test_schema_action.py` -- version assertion

- [ ] **Step 1: Bump schema version**

In `simulink_cli/core.py`, change `"version": "2.8"` to `"version": "2.9"`.

- [ ] **Step 2: Update schema test**

In `tests/test_schema_action.py`, change `self.assertEqual(self.schema["version"], "2.8")` to `self.assertEqual(self.schema["version"], "2.9")`.

- [ ] **Step 3: Run full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: All tests PASS, zero failures.

- [ ] **Step 4: Commit**

```bash
git add simulink_cli/core.py tests/test_schema_action.py
git commit -m "chore: bump schema version to 2.9"
```
