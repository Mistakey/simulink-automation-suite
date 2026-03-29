import unittest
from unittest.mock import patch

from simulink_cli.actions import connections
from tests.fakes import FakeConnectionsEngine, FakeSPSConnectionsEngine, FakeStrictMatlabHandleEngine


def _conn_args(target, model=None, direction="both", depth=1, detail="summary",
               include_handles=False, max_edges=None, fields=None, session=None):
    return {
        "target": target, "model": model, "direction": direction, "depth": depth,
        "detail": detail, "include_handles": include_handles, "max_edges": max_edges,
        "fields": fields, "session": session,
    }


class ConnectionsBehaviorTests(unittest.TestCase):
    def test_connections_signal_name_fallback_preserves_warning(self):
        class WarningThenMissingSignalNameEngine(FakeConnectionsEngine):
            def __init__(self):
                super().__init__()
                self.warning_log = []

            def get_param(self, target, param_name):
                if isinstance(target, (int, float)) and int(target) in self.line_meta:
                    if param_name == "Name":
                        self.warning_log.append("Variant warning")
                        raise RuntimeError("boom")
                return super().get_param(target, param_name)

        eng = WarningThenMissingSignalNameEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/B", detail="ports"))
        self.assertEqual(result["warnings"], ["Variant warning"])
        self.assertEqual(result["edges"][0]["signal_name"], "")

    def test_connections_port_info_failure_preserves_prior_warning(self):
        class WarningThenMissingPortNumberEngine(FakeConnectionsEngine):
            def __init__(self):
                super().__init__()
                self.warning_log = []

            def get_param(self, target, param_name):
                if target == 21 and param_name == "Parent":
                    self.warning_log.append("Variant warning")
                if target == 21 and param_name == "PortNumber":
                    raise RuntimeError("boom")
                return super().get_param(target, param_name)

        eng = WarningThenMissingPortNumberEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/B", detail="ports"))
        self.assertEqual(result["error"], "runtime_error")
        self.assertEqual(result["details"]["warnings"], ["Variant warning"])

    def test_default_summary_returns_one_hop_neighbors(self):
        eng = FakeConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/B"))
        self.assertEqual(result["target"], "m1/B")
        self.assertEqual(result["direction"], "both")
        self.assertEqual(result["depth"], 1)
        self.assertEqual(result["upstream_blocks"], ["m1/A"])
        self.assertEqual(result["downstream_blocks"], ["m1/C"])

    def test_direction_upstream_only(self):
        eng = FakeConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/B", direction="upstream"))
        self.assertEqual(result["upstream_blocks"], ["m1/A"])
        self.assertEqual(result["downstream_blocks"], [])

    def test_direction_downstream_depth_two(self):
        eng = FakeConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/A", direction="downstream", depth=2))
        self.assertEqual(result["upstream_blocks"], [])
        self.assertEqual(result["downstream_blocks"], ["m1/B", "m1/C"])

    def test_detail_ports_includes_edge_endpoints(self):
        eng = FakeConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/B", detail="ports"))
        self.assertTrue(result["edges"])
        first = result["edges"][0]
        self.assertIn("src_block", first)
        self.assertIn("src_port", first)
        self.assertIn("dst_block", first)
        self.assertIn("dst_port", first)
        self.assertNotIn("line_handle", first)

    def test_detail_lines_with_handles_includes_line_handle(self):
        eng = FakeConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(
                target="m1/B", detail="lines", include_handles=True,
            ))
        self.assertTrue(result["edges"])
        self.assertIn("line_handle", result["edges"][0])

    def test_invalid_target_returns_block_not_found(self):
        eng = FakeConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/UNKNOWN"))
        self.assertEqual(result["error"], "block_not_found")

    def test_connections_supports_double_handles_without_int_cast_errors(self):
        eng = FakeStrictMatlabHandleEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/B"))
        self.assertNotIn("error", result)
        self.assertEqual(result["upstream_blocks"], ["m1/A"])
        self.assertEqual(result["downstream_blocks"], ["m1/C"])


class PhysicalConnectionsTests(unittest.TestCase):
    def test_physical_neighbors_appear_in_dedicated_field(self):
        eng = FakeSPSConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/PSrc"))
        self.assertNotIn("error", result)
        self.assertIn("physical_neighbors", result)
        self.assertEqual(sorted(result["physical_neighbors"]), ["m1/PLoad1", "m1/PLoad2"])

    def test_physical_edges_have_type_physical_in_detail_ports(self):
        eng = FakeSPSConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/PSrc", detail="ports"))
        self.assertNotIn("error", result)
        physical_edges = [e for e in result["edges"] if e.get("type") == "physical"]
        self.assertEqual(len(physical_edges), 2)

    def test_signal_edges_have_type_signal_in_detail_ports(self):
        eng = FakeConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/B", detail="ports"))
        self.assertTrue(all(e.get("type") == "signal" for e in result["edges"]))

    def test_physical_neighbors_found_regardless_of_direction(self):
        eng = FakeSPSConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/PSrc", direction="downstream"))
        self.assertIn("physical_neighbors", result)
        self.assertEqual(len(result["physical_neighbors"]), 2)

    def test_physical_neighbors_not_mixed_into_upstream_downstream(self):
        eng = FakeSPSConnectionsEngine()
        with patch.object(connections, 'safe_connect_to_session', return_value=(eng, None)):
            result = connections.execute(_conn_args(target="m1/PSrc"))
        self.assertEqual(result["upstream_blocks"], [])
        self.assertEqual(result["downstream_blocks"], [])


if __name__ == "__main__":
    unittest.main()
