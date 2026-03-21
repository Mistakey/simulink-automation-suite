"""Consolidated output control tests — max_X truncation and fields projection."""

import unittest
from unittest.mock import patch

from simulink_cli.actions import scan, find, inspect_block, connections
from tests.fakes import (
    FakeScanOutputEngine,
    FakeFindEngine,
    FakeInspectOutputEngine,
    FakeConnectionsEngine,
)


class ScanOutputControlsTests(unittest.TestCase):
    def _run_scan(self, **kwargs):
        args = {
            "model": "m1", "subsystem": None, "recursive": False,
            "hierarchy": False, "session": None, "max_blocks": None, "fields": None,
        }
        args.update(kwargs)
        with patch.object(scan, 'safe_connect_to_session',
                          return_value=(FakeScanOutputEngine(), None)):
            return scan.execute(args)

    def test_max_blocks_truncates_and_reports_metadata(self):
        result = self._run_scan(max_blocks=2)
        self.assertEqual(result["total_count"], 3)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["blocks"]), 2)

    def test_fields_projects_block_entries(self):
        result = self._run_scan(fields=["name"])
        self.assertTrue(result["blocks"])
        self.assertEqual(sorted(result["blocks"][0].keys()), ["name"])

    def test_validate_rejects_non_positive_max_blocks(self):
        args = {
            "model": "m1", "subsystem": None, "recursive": False,
            "hierarchy": False, "session": None, "max_blocks": 0, "fields": None,
        }
        result = scan.validate(args)
        self.assertEqual(result["error"], "invalid_input")


class FindOutputControlsTests(unittest.TestCase):
    def _make_engine(self):
        blocks = [f"my_model/Block{i}" for i in range(5)]
        return FakeFindEngine(
            models=["my_model"],
            find_results={"my_model": blocks},
            valid_handles={"my_model"} | set(blocks),
        )

    def _run_find(self, **kwargs):
        args = {
            "model": "my_model", "subsystem": None, "name": "Block",
            "block_type": None, "session": None, "max_results": 200, "fields": None,
        }
        args.update(kwargs)
        with patch.object(find, 'safe_connect_to_session',
                          return_value=(self._make_engine(), None)):
            return find.execute(args)

    def test_max_results_clips_output(self):
        result = self._run_find(max_results=3)
        self.assertEqual(result["total_results"], 5)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["results"]), 3)

    def test_fields_projection(self):
        result = self._run_find(fields=["path", "type"])
        for item in result["results"]:
            self.assertIn("path", item)
            self.assertIn("type", item)
            self.assertNotIn("name", item)


class InspectOutputControlsTests(unittest.TestCase):
    def _run_inspect(self, **kwargs):
        args = {
            "model": None, "target": "m/b", "param": "All",
            "active_only": False, "strict_active": False,
            "resolve_effective": False, "summary": False,
            "session": None, "max_params": None, "fields": None,
        }
        args.update(kwargs)
        with patch.object(inspect_block, 'safe_connect_to_session',
                          return_value=(FakeInspectOutputEngine(), None)):
            return inspect_block.execute(args)

    def test_max_params_truncates_and_reports_metadata(self):
        result = self._run_inspect(max_params=1)
        self.assertEqual(result["total_params"], 2)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["available_params"]), 1)

    def test_fields_projects_top_level_keys(self):
        result = self._run_inspect(fields=["target", "values"])
        self.assertIn("target", result)
        self.assertIn("values", result)
        self.assertNotIn("available_params", result)

    def test_validate_rejects_non_positive_max_params(self):
        args = {
            "model": None, "target": "m/b", "param": "All",
            "active_only": False, "strict_active": False,
            "resolve_effective": False, "summary": False,
            "session": None, "max_params": 0, "fields": None,
        }
        result = inspect_block.validate(args)
        self.assertEqual(result["error"], "invalid_input")


class ConnectionsOutputControlsTests(unittest.TestCase):
    def _run_connections(self, **kwargs):
        args = {
            "model": None, "target": "m1/B", "direction": "both",
            "depth": 1, "detail": "ports", "include_handles": False,
            "max_edges": None, "fields": None, "session": None,
        }
        args.update(kwargs)
        with patch.object(connections, 'safe_connect_to_session',
                          return_value=(FakeConnectionsEngine(), None)):
            return connections.execute(args)

    def test_max_edges_truncates_and_reports_metadata(self):
        result = self._run_connections(max_edges=1)
        self.assertEqual(result["total_edges"], 2)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["edges"]), 1)

    def test_fields_projects_top_level_keys(self):
        result = self._run_connections(fields=["target", "edges"])
        self.assertIn("target", result)
        self.assertIn("edges", result)
        self.assertNotIn("direction", result)

    def test_validate_rejects_non_positive_max_edges(self):
        args = {
            "model": None, "target": "m1/B", "direction": "both",
            "depth": 1, "detail": "ports", "include_handles": False,
            "max_edges": 0, "fields": None, "session": None,
        }
        result = connections.validate(args)
        self.assertEqual(result["error"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
