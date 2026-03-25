"""Tests for block_add action."""

import unittest

from simulink_cli import matlab_transport
from tests.fakes import FakeBlockEngine


class TransportAddBlockTests(unittest.TestCase):
    def test_add_block_function_exists(self):
        self.assertTrue(callable(matlab_transport.add_block))


class FakeBlockEngineTests(unittest.TestCase):
    def test_add_block_creates_block(self):
        eng = FakeBlockEngine(
            loaded_models=["my_model"],
            library_sources=["simulink/Math Operations/Gain"],
        )
        eng.add_block("simulink/Math Operations/Gain", "my_model/Gain1", nargout=0)
        self.assertEqual(eng.get_param("my_model/Gain1", "Handle", nargout=1), 1.0)

    def test_add_block_duplicate_raises(self):
        eng = FakeBlockEngine(
            loaded_models=["my_model"],
            library_sources=["simulink/Math Operations/Gain"],
            blocks=["my_model/Gain1"],
        )
        with self.assertRaises(RuntimeError):
            eng.add_block("simulink/Math Operations/Gain", "my_model/Gain1", nargout=0)

    def test_get_param_model_not_loaded_raises(self):
        eng = FakeBlockEngine()
        with self.assertRaises(RuntimeError):
            eng.get_param("missing_model", "Handle", nargout=1)

    def test_get_param_library_source_returns_handle(self):
        eng = FakeBlockEngine(library_sources=["simulink/Math Operations/Gain"])
        self.assertEqual(
            eng.get_param("simulink/Math Operations/Gain", "Handle", nargout=1), 1.0
        )


if __name__ == "__main__":
    unittest.main()
