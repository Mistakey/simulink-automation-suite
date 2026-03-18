import unittest
from unittest.mock import patch

from simulink_cli.actions import find
from tests.fakes import FakeFindEngine


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
            "model": "my_model",
            "subsystem": None,
            "name": "Block",
            "block_type": None,
            "session": None,
            "max_results": 200,
            "fields": None,
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
            self.assertNotIn("parent", item)

    def test_max_results_and_fields_combined(self):
        result = self._run_find(max_results=2, fields=["path"])
        self.assertEqual(result["total_results"], 5)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(sorted(result["results"][0].keys()), ["path"])


if __name__ == "__main__":
    unittest.main()
