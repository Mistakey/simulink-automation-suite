# Connections Action Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a read-only `connections` action that returns upstream/downstream module relationships with progressive detail levels and JSON/flags parity.

**Architecture:** Extend the existing CLI contract in `sl_core.py` with a standalone `connections` action and route it to a new traversal function in `sl_scan.py`. The traversal computes one-hop or multi-hop graph neighborhoods using Simulink connection metadata, then projects output by `detail` level (`summary|ports|lines`). Keep current `scan` behavior unchanged and reuse existing stable error contracts.

**Tech Stack:** Python 3.10+, `argparse`, `unittest`, existing runtime modules under `skills/simulink_scan/scripts/`

---

**Execution notes**

- Use @superpowers:test-driven-development for each behavior change.
- Keep commits small and aligned to tasks.
- Verify with `python -m unittest ...` commands shown in each task.

### Task 1: Add Failing Behavior Tests for `connections`

**Files:**
- Create: `tests/test_connections_behavior.py`
- Test: `tests/test_connections_behavior.py`

**Step 1: Write the failing test**

```python
import unittest

from skills.simulink_scan.scripts.sl_scan import get_block_connections


class FakeConnectionsEngine:
    def __init__(self):
        self.valid_blocks = {"m1/A", "m1/B", "m1/C", "m1/D"}
        self.port_handles = {
            "m1/A": {"Inport": [], "Outport": [101]},
            "m1/B": {"Inport": [201], "Outport": [202]},
            "m1/C": {"Inport": [301], "Outport": []},
            "m1/D": {"Inport": [401], "Outport": []},
        }
        self.line_of_port = {101: 1001, 201: 1001, 202: 1002, 301: 1002, 401: -1}
        self.line_meta = {
            1001: {"SrcPortHandle": 101, "DstPortHandle": [201], "Name": "sig_ab"},
            1002: {"SrcPortHandle": 202, "DstPortHandle": [301], "Name": "sig_bc"},
        }
        self.port_parent = {101: "m1/A", 201: "m1/B", 202: "m1/B", 301: "m1/C"}
        self.port_number = {101: 1, 201: 1, 202: 1, 301: 1}

    def get_param(self, target, name):
        if name == "Handle":
            if target not in self.valid_blocks:
                raise RuntimeError("not found")
            return 1
        if name == "PortHandles":
            return self.port_handles[target]
        if name == "Line":
            return self.line_of_port[target]
        if name in ("SrcPortHandle", "DstPortHandle", "Name"):
            return self.line_meta[target][name]
        if name == "Parent":
            return self.port_parent[target]
        if name == "PortNumber":
            return self.port_number[target]
        raise RuntimeError(f"unsupported param: {name}")


class ConnectionsBehaviorTests(unittest.TestCase):
    def test_default_summary_returns_one_hop_upstream_and_downstream(self):
        result = get_block_connections(FakeConnectionsEngine(), block_path="m1/B")
        self.assertEqual(result["target"], "m1/B")
        self.assertEqual(result["depth"], 1)
        self.assertEqual(result["direction"], "both")
        self.assertEqual(result["upstream_blocks"], ["m1/A"])
        self.assertEqual(result["downstream_blocks"], ["m1/C"])

    def test_direction_upstream_filters_output(self):
        result = get_block_connections(
            FakeConnectionsEngine(), block_path="m1/B", direction="upstream"
        )
        self.assertEqual(result["upstream_blocks"], ["m1/A"])
        self.assertEqual(result["downstream_blocks"], [])

    def test_depth_two_reaches_second_hop(self):
        result = get_block_connections(
            FakeConnectionsEngine(), block_path="m1/A", direction="downstream", depth=2
        )
        self.assertEqual(result["downstream_blocks"], ["m1/B", "m1/C"])

    def test_detail_ports_includes_edge_endpoints(self):
        result = get_block_connections(
            FakeConnectionsEngine(), block_path="m1/B", detail="ports"
        )
        self.assertTrue(result["edges"])
        self.assertIn("src_block", result["edges"][0])
        self.assertIn("dst_block", result["edges"][0])

    def test_detail_lines_with_handles_includes_line_handle(self):
        result = get_block_connections(
            FakeConnectionsEngine(),
            block_path="m1/B",
            detail="lines",
            include_handles=True,
        )
        self.assertTrue(result["edges"])
        self.assertIn("line_handle", result["edges"][0])

    def test_invalid_target_returns_block_not_found(self):
        result = get_block_connections(FakeConnectionsEngine(), block_path="m1/MISSING")
        self.assertEqual(result["error"], "block_not_found")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_connections_behavior -v`  
Expected: FAIL with `ImportError` or missing symbol `get_block_connections`.

**Step 3: Write minimal implementation**

Create placeholder function in `skills/simulink_scan/scripts/sl_scan.py`:

```python
def get_block_connections(
    eng,
    block_path,
    model_name=None,
    direction="both",
    depth=1,
    detail="summary",
    include_handles=False,
):
    raise NotImplementedError("connections action not implemented yet")
```

**Step 4: Run test to verify it fails for the right reason**

Run: `python -m unittest tests.test_connections_behavior -v`  
Expected: FAIL with `NotImplementedError`, proving tests call the new API.

**Step 5: Commit**

```bash
git add tests/test_connections_behavior.py skills/simulink_scan/scripts/sl_scan.py
git commit -m "test(connections): add failing behavior coverage"
```

### Task 2: Implement `get_block_connections` Traversal and Projection

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_scan.py`
- Test: `tests/test_connections_behavior.py`

**Step 1: Write/extend failing test for cycle-safe traversal**

```python
def test_cycle_graph_does_not_loop_forever(self):
    eng = FakeConnectionsEngine()
    # Add line C -> A to create a cycle.
    eng.port_handles["m1/C"]["Outport"] = [302]
    eng.port_parent[302] = "m1/C"
    eng.port_number[302] = 1
    eng.line_of_port[302] = 1003
    eng.line_meta[1003] = {"SrcPortHandle": 302, "DstPortHandle": [101], "Name": "sig_ca"}
    result = get_block_connections(eng, block_path="m1/A", direction="downstream", depth=3)
    self.assertTrue(result["downstream_blocks"])
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_connections_behavior.ConnectionsBehaviorTests.test_cycle_graph_does_not_loop_forever -v`  
Expected: FAIL until traversal is implemented with visited-set protection.

**Step 3: Write minimal implementation**

Add helpers and traversal in `sl_scan.py`:

```python
def _to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _valid_handle(value):
    try:
        return int(value) > 0
    except Exception:
        return False


def _port_info(eng, port_handle):
    return {
        "block": str(eng.get_param(port_handle, "Parent")),
        "port": int(eng.get_param(port_handle, "PortNumber")),
    }


def _collect_block_edges(eng, block_path):
    edges = []
    ports = eng.get_param(block_path, "PortHandles")
    for out_handle in _to_list(ports.get("Outport")):
        line_handle = eng.get_param(out_handle, "Line")
        if not _valid_handle(line_handle):
            continue
        src = _port_info(eng, out_handle)
        for dst_handle in _to_list(eng.get_param(line_handle, "DstPortHandle")):
            if not _valid_handle(dst_handle):
                continue
            dst = _port_info(eng, dst_handle)
            edges.append(
                {
                    "src_block": src["block"],
                    "src_port": src["port"],
                    "dst_block": dst["block"],
                    "dst_port": dst["port"],
                    "signal_name": str(eng.get_param(line_handle, "Name") or ""),
                    "line_handle": line_handle,
                }
            )
    return edges
```

Then implement BFS by `direction` and `depth`, dedupe edges, and project result by `detail`.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_connections_behavior -v`  
Expected: PASS all `ConnectionsBehaviorTests`.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_scan.py tests/test_connections_behavior.py
git commit -m "feat(connections): add traversal and detail projection"
```

### Task 3: Add Parser/Schema/JSON Failing Tests for New Action

**Files:**
- Modify: `tests/test_schema_action.py`
- Modify: `tests/test_json_input_mode.py`
- Modify: `tests/test_input_validation.py`

**Step 1: Write the failing tests**

`tests/test_schema_action.py`:

```python
def test_schema_action_includes_connections_contract(self):
    args = parse_request_args(self.parser, ["schema"])
    result = run_action(args)
    self.assertIn("connections", result["actions"])
```

`tests/test_json_input_mode.py`:

```python
def test_parse_request_args_accepts_json_connections_request(self):
    args = parse_request_args(
        self.parser,
        ['--json', '{"action":"connections","target":"m1/Gain","depth":1}'],
    )
    self.assertEqual(args.action, "connections")
    self.assertEqual(args.target, "m1/Gain")
    self.assertEqual(args.depth, 1)
```

`tests/test_input_validation.py`:

```python
def test_validate_args_rejects_invalid_connections_direction(self):
    args = argparse.Namespace(
        action="connections",
        model=None,
        target="m1/Gain",
        session=None,
        direction="sideways",
        depth=1,
        detail="summary",
        include_handles=False,
    )
    result = validate_args(args)
    self.assertEqual(result["error"], "invalid_input")
```

**Step 2: Run tests to verify they fail**

Run:  
`python -m unittest tests.test_schema_action tests.test_json_input_mode tests.test_input_validation -v`  
Expected: FAIL because parser/schema/validation do not yet support `connections`.

**Step 3: Minimal temporary implementation shim**

Add scaffolding in `sl_core.py` (JSON field map and parser subcommand only) without routing:

```python
_JSON_FIELD_TYPES["connections"] = {
    "model": str,
    "target": str,
    "session": str,
    "direction": str,
    "depth": int,
    "detail": str,
    "include_handles": bool,
}
```

**Step 4: Re-run tests to ensure failures move to runtime/routing gaps**

Run:  
`python -m unittest tests.test_schema_action tests.test_json_input_mode tests.test_input_validation -v`  
Expected: parser-level failures resolved; remaining failures indicate missing `run_action` wiring and validation rules.

**Step 5: Commit**

```bash
git add tests/test_schema_action.py tests/test_json_input_mode.py tests/test_input_validation.py skills/simulink_scan/scripts/sl_core.py
git commit -m "test(connections): add parser and contract coverage"
```

### Task 4: Implement `connections` in `sl_core.py`

**Files:**
- Modify: `skills/simulink_scan/scripts/sl_core.py`
- Modify: `skills/simulink_scan/scripts/sl_scan.py`
- Test: `tests/test_schema_action.py`
- Test: `tests/test_json_input_mode.py`
- Test: `tests/test_input_validation.py`
- Test: `tests/test_connections_behavior.py`

**Step 1: Write failing integration test for action routing**

Add to `tests/test_input_validation.py`:

```python
def test_run_action_connections_routes_to_scan_layer(self):
    args = argparse.Namespace(
        action="connections",
        model=None,
        target="m1/Gain",
        session=None,
        direction="both",
        depth=1,
        detail="summary",
        include_handles=False,
    )
    result = run_action(args)
    self.assertIn("error", result)
```

**Step 2: Run focused tests to verify failure**

Run:  
`python -m unittest tests.test_input_validation.InputValidationTests.test_run_action_connections_routes_to_scan_layer -v`  
Expected: FAIL because `run_action` lacks `connections` branch.

**Step 3: Write minimal implementation**

In `sl_core.py`:

- import `get_block_connections`
- add `connections` to `_JSON_FIELD_TYPES`
- include `connections` in `build_schema_payload()`
- add `connections` parser:

```python
connections_parser = subparsers.add_parser(
    "connections", help="Read upstream/downstream block connections"
)
connections_parser.add_argument("--model", help="Optional specific model name")
connections_parser.add_argument("--target", required=True, help="Block path to analyze")
connections_parser.add_argument("--session", help="Session override for this command")
connections_parser.add_argument(
    "--direction",
    choices=["upstream", "downstream", "both"],
    default="both",
    help="Traversal direction from target block",
)
connections_parser.add_argument(
    "--depth", type=int, default=1, help="Traversal depth in hops (must be > 0)"
)
connections_parser.add_argument(
    "--detail",
    choices=["summary", "ports", "lines"],
    default="summary",
    help="Output detail level",
)
connections_parser.add_argument(
    "--include-handles",
    action="store_true",
    help="Include line handles in lines detail output",
)
```

In `validate_args(args)`:

```python
if args.action == "connections":
    if getattr(args, "depth", 1) <= 0:
        return _invalid_input("depth", "must be greater than zero")
    if getattr(args, "direction", "both") not in {"upstream", "downstream", "both"}:
        return _invalid_input("direction", "must be one of upstream,downstream,both")
    if getattr(args, "detail", "summary") not in {"summary", "ports", "lines"}:
        return _invalid_input("detail", "must be one of summary,ports,lines")
```

In `run_action(args)`:

```python
if args.action == "connections":
    return get_block_connections(
        eng,
        block_path=args.target,
        model_name=getattr(args, "model", None),
        direction=getattr(args, "direction", "both"),
        depth=getattr(args, "depth", 1),
        detail=getattr(args, "detail", "summary"),
        include_handles=getattr(args, "include_handles", False),
    )
```

**Step 4: Run tests to verify pass**

Run:  
`python -m unittest tests.test_schema_action tests.test_json_input_mode tests.test_input_validation tests.test_connections_behavior -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/scripts/sl_core.py skills/simulink_scan/scripts/sl_scan.py tests/test_schema_action.py tests/test_json_input_mode.py tests/test_input_validation.py tests/test_connections_behavior.py
git commit -m "feat(connections): wire parser schema json and runtime routing"
```

### Task 5: Add Docs Contract Failing Tests for `connections`

**Files:**
- Modify: `tests/test_docs_contract.py`

**Step 1: Write the failing tests**

```python
def test_skill_docs_connections_action(self):
    text = SKILL_PATH.read_text(encoding="utf-8")
    self.assertIn("connections", text)


def test_reference_docs_connections_action(self):
    text = REFERENCE_PATH.read_text(encoding="utf-8")
    self.assertIn("## Connections Action", text)


def test_scenarios_include_connections_recovery(self):
    text = SCENARIOS_PATH.read_text(encoding="utf-8")
    self.assertIn("connections", text)
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_docs_contract -v`  
Expected: FAIL due to missing `connections` docs.

**Step 3: Keep code unchanged**

No runtime changes here; this task enforces docs-first contract for the new capability.

**Step 4: Re-run to keep failures visible**

Run: `python -m unittest tests.test_docs_contract -v`  
Expected: still FAIL until docs are updated in Task 6.

**Step 5: Commit**

```bash
git add tests/test_docs_contract.py
git commit -m "test(docs): require connections action documentation"
```

### Task 6: Update Skill/Reference/README Docs

**Files:**
- Modify: `skills/simulink_scan/SKILL.md`
- Modify: `skills/simulink_scan/reference.md`
- Modify: `skills/simulink_scan/test-scenarios.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Test: `tests/test_docs_contract.py`

**Step 1: Update docs with `connections` contract**

Use this exact capability statement in `SKILL.md` action section:

```markdown
3. Connection analysis (upstream/downstream) -> `connections`
```

Add execution template:

```markdown
- Analyze block connections:
  - `python -m skills.simulink_scan connections --target "<block>" --direction both --depth 1 --detail summary`
```

In `reference.md`, add section:

```markdown
## Connections Action

- `python -m skills.simulink_scan connections --target "<block>"`
- `python -m skills.simulink_scan connections --target "<block>" --direction upstream --depth 2 --detail ports`
- `python -m skills.simulink_scan --json "{\"action\":\"connections\",\"target\":\"<block>\",\"detail\":\"summary\"}"`
```

**Step 2: Run docs contract test**

Run: `python -m unittest tests.test_docs_contract -v`  
Expected: PASS.

**Step 3: Run combined targeted tests**

Run:  
`python -m unittest tests.test_connections_behavior tests.test_schema_action tests.test_json_input_mode tests.test_docs_contract -v`  
Expected: PASS.

**Step 4: Commit**

```bash
git add skills/simulink_scan/SKILL.md skills/simulink_scan/reference.md skills/simulink_scan/test-scenarios.md README.md README.zh-CN.md tests/test_docs_contract.py
git commit -m "docs(connections): publish action contract and examples"
```

### Task 7: Full Verification Before Completion

**Files:**
- Verify only

**Step 1: Run full test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`  
Expected: all tests PASS.

**Step 2: Validate plugin manifest contract**

Run: `python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v`  
Expected: PASS.

**Step 3: Inspect diff for scope discipline**

Run: `git diff --name-only HEAD~7..HEAD`  
Expected: only runtime/parser/tests/docs files related to `connections`.

**Step 4: Final integration commit**

```bash
git log --oneline -n 7
```

Expected: clearly scoped commits for tests, runtime, parser, and docs in order.

**Step 5: Prepare PR summary checklist**

Document:

- `connections` action supports flags + JSON.
- default output is concise (`summary`, `depth=1`, `direction=both`).
- detail escalation works (`ports`, `lines`, optional handles).
- read-only boundary preserved.
