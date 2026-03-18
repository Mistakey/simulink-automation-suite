import unittest
from unittest import mock

from simulink_cli.actions import connections


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
        self.port_parent = {
            11: "m1/A",
            14: "m1/A",
            21: "m1/B",
            22: "m1/B",
            31: "m1/C",
            32: "m1/C",
        }
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


class ConnectionsOutputControlsTests(unittest.TestCase):
    def _run_connections(self, **kwargs):
        args = {
            "model": None,
            "target": "m1/B",
            "direction": "both",
            "depth": 1,
            "detail": "ports",
            "include_handles": False,
            "max_edges": None,
            "fields": None,
            "session": None,
        }
        args.update(kwargs)
        with mock.patch(
            "simulink_cli.actions.connections.safe_connect_to_session",
            return_value=(FakeConnectionsEngine(), None),
        ):
            return connections.execute(args)

    def test_connections_max_edges_truncates_and_reports_metadata(self):
        result = self._run_connections(max_edges=1)
        self.assertEqual(result["total_edges"], 2)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["edges"]), 1)

    def test_connections_fields_projects_top_level_keys(self):
        result = self._run_connections(fields=["target", "edges"])
        self.assertIn("target", result)
        self.assertIn("edges", result)
        self.assertNotIn("direction", result)
        self.assertNotIn("upstream_blocks", result)

    def test_validate_rejects_non_positive_connections_max_edges(self):
        args = {
            "model": None,
            "target": "m1/B",
            "direction": "both",
            "depth": 1,
            "detail": "ports",
            "include_handles": False,
            "max_edges": 0,
            "fields": None,
            "session": None,
        }
        result = connections.validate(args)
        self.assertEqual(result["error"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
