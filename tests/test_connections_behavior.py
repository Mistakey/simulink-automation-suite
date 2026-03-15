import unittest

from skills.simulink_scan.scripts.sl_connections import get_block_connections


class FakeConnectionsEngine:
    def __init__(self):
        self.blocks = {"m1/A", "m1/B", "m1/C"}
        self.port_handles = {
            "m1/A": {"Inport": [14], "Outport": [11]},
            "m1/B": {"Inport": [21], "Outport": [22]},
            "m1/C": {"Inport": [31], "Outport": [32]},
        }
        self.port_line = {11: 1001, 14: 1003, 21: 1001, 22: 1002, 31: 1002, 32: 1003}
        self.line_meta = {
            1001: {"SrcPortHandle": 11, "DstPortHandle": [21], "Name": "sig_ab"},
            1002: {"SrcPortHandle": 22, "DstPortHandle": [31], "Name": "sig_bc"},
            1003: {"SrcPortHandle": 32, "DstPortHandle": [14], "Name": "sig_ca"},
        }
        self.port_parent = {11: "m1/A", 14: "m1/A", 21: "m1/B", 22: "m1/B", 31: "m1/C", 32: "m1/C"}
        self.port_number = {11: 1, 14: 1, 21: 1, 22: 1, 31: 1, 32: 1}

    def get_param(self, target, param_name):
        if isinstance(target, str) and param_name == "Handle":
            if target not in self.blocks:
                raise RuntimeError("not found")
            return 1
        if isinstance(target, str) and param_name == "PortHandles":
            return self.port_handles[target]
        if isinstance(target, (int, float)):
            key = int(target)
            if param_name == "Line":
                return self.port_line.get(key, -1)
            if key in self.line_meta:
                return self.line_meta[key][param_name]
            if param_name == "Parent":
                return self.port_parent[key]
            if param_name == "PortNumber":
                return self.port_number[key]
        raise RuntimeError(f"unsupported param: {param_name}")


class FakeStrictMatlabHandleEngine:
    """Emulates MATLAB engine behavior that rejects Python int handles."""

    def __init__(self):
        self.blocks = {"m1/A", "m1/B", "m1/C"}
        self.port_handles = {
            "m1/A": {"Inport": [14.0], "Outport": [11.0]},
            "m1/B": {"Inport": [21.0], "Outport": [22.0]},
            "m1/C": {"Inport": [31.0], "Outport": [32.0]},
        }
        self.port_line = {
            11: 1001.0,
            14: 1003.0,
            21: 1001.0,
            22: 1002.0,
            31: 1002.0,
            32: 1003.0,
        }
        self.line_meta = {
            1001: {"SrcPortHandle": 11.0, "DstPortHandle": [21.0], "Name": "sig_ab"},
            1002: {"SrcPortHandle": 22.0, "DstPortHandle": [31.0], "Name": "sig_bc"},
            1003: {"SrcPortHandle": 32.0, "DstPortHandle": [14.0], "Name": "sig_ca"},
        }
        self.port_parent = {
            11: "m1/A",
            14: "m1/A",
            21: "m1/B",
            22: "m1/B",
            31: "m1/C",
            32: "m1/C",
        }
        self.port_number = {11: 1.0, 14: 1.0, 21: 1.0, 22: 1.0, 31: 1.0, 32: 1.0}

    def get_param(self, target, param_name):
        if isinstance(target, str) and param_name == "Handle":
            if target not in self.blocks:
                raise RuntimeError("not found")
            return 1.0
        if isinstance(target, str) and param_name == "PortHandles":
            return self.port_handles[target]

        if isinstance(target, int):
            raise RuntimeError(
                "The first input to get_param must be of type 'double', 'char' or 'cell'."
            )

        if isinstance(target, float):
            key = int(target)
            if param_name == "Line":
                return self.port_line.get(key, -1.0)
            if key in self.line_meta and param_name in self.line_meta[key]:
                return self.line_meta[key][param_name]
            if param_name == "Parent":
                return self.port_parent[key]
            if param_name == "PortNumber":
                return self.port_number[key]

        raise RuntimeError(f"unsupported param: {param_name}")


class ConnectionsBehaviorTests(unittest.TestCase):
    def test_default_summary_returns_one_hop_neighbors(self):
        result = get_block_connections(FakeConnectionsEngine(), block_path="m1/B")
        self.assertEqual(result["target"], "m1/B")
        self.assertEqual(result["direction"], "both")
        self.assertEqual(result["depth"], 1)
        self.assertEqual(result["upstream_blocks"], ["m1/A"])
        self.assertEqual(result["downstream_blocks"], ["m1/C"])

    def test_direction_upstream_only(self):
        result = get_block_connections(
            FakeConnectionsEngine(), block_path="m1/B", direction="upstream"
        )
        self.assertEqual(result["upstream_blocks"], ["m1/A"])
        self.assertEqual(result["downstream_blocks"], [])

    def test_direction_downstream_depth_two(self):
        result = get_block_connections(
            FakeConnectionsEngine(), block_path="m1/A", direction="downstream", depth=2
        )
        self.assertEqual(result["upstream_blocks"], [])
        self.assertEqual(result["downstream_blocks"], ["m1/B", "m1/C"])

    def test_detail_ports_includes_edge_endpoints(self):
        result = get_block_connections(
            FakeConnectionsEngine(), block_path="m1/B", detail="ports"
        )
        self.assertTrue(result["edges"])
        first = result["edges"][0]
        self.assertIn("src_block", first)
        self.assertIn("src_port", first)
        self.assertIn("dst_block", first)
        self.assertIn("dst_port", first)
        self.assertNotIn("line_handle", first)

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
        result = get_block_connections(
            FakeConnectionsEngine(), block_path="m1/UNKNOWN"
        )
        self.assertEqual(result["error"], "block_not_found")

    def test_connections_supports_double_handles_without_int_cast_errors(self):
        result = get_block_connections(
            FakeStrictMatlabHandleEngine(), block_path="m1/B"
        )
        self.assertNotIn("error", result)
        self.assertEqual(result["upstream_blocks"], ["m1/A"])
        self.assertEqual(result["downstream_blocks"], ["m1/C"])


if __name__ == "__main__":
    unittest.main()
