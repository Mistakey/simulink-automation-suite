import unittest
from unittest.mock import patch

from simulink_cli.actions import connections
from tests.fakes import FakeConnectionsEngine


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
        with patch.object(connections, 'safe_connect_to_session',
                          return_value=(FakeConnectionsEngine(), None)):
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
