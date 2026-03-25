"""Tests for block_add action."""

import unittest
from unittest.mock import patch

from simulink_cli import matlab_transport
from tests.fakes import FakeBlockEngine
from simulink_cli.actions import block_cmd


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


class BlockAddValidationTests(unittest.TestCase):
    def test_missing_source_returns_error(self):
        result = block_cmd.validate({"destination": "m/Gain1", "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_destination_returns_error(self):
        result = block_cmd.validate({"source": "simulink/Gain", "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_args_returns_none(self):
        result = block_cmd.validate(
            {
                "source": "simulink/Math Operations/Gain",
                "destination": "my_model/Gain1",
                "session": None,
            }
        )
        self.assertIsNone(result)


class BlockAddExecuteTests(unittest.TestCase):
    def _make_engine(self, **kwargs):
        defaults = {
            "loaded_models": ["my_model"],
            "library_sources": ["simulink/Math Operations/Gain"],
        }
        defaults.update(kwargs)
        return FakeBlockEngine(**defaults)

    def _run(self, args, engine=None):
        if engine is None:
            engine = self._make_engine()
        with patch.object(block_cmd, "safe_connect_to_session", return_value=(engine, None)):
            return block_cmd.execute(args)

    def _default_args(self, **overrides):
        args = {
            "source": "simulink/Math Operations/Gain",
            "destination": "my_model/Gain1",
            "session": None,
        }
        args.update(overrides)
        return args

    def test_adds_block_successfully(self):
        result = self._run(self._default_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "block_add")
        self.assertEqual(result["source"], "simulink/Math Operations/Gain")
        self.assertEqual(result["destination"], "my_model/Gain1")
        self.assertTrue(result["verified"])

    def test_model_not_loaded_returns_error(self):
        eng = self._make_engine(loaded_models=[])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_not_found")

    def test_source_not_found_returns_error(self):
        eng = self._make_engine(library_sources=[])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "source_not_found")

    def test_block_already_exists_returns_error(self):
        eng = self._make_engine(blocks=["my_model/Gain1"])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "block_already_exists")

    def test_runtime_error_on_add_block_failure(self):
        eng = self._make_engine()
        with patch.object(
            matlab_transport,
            "add_block",
            side_effect=RuntimeError("MATLAB crashed"),
        ):
            result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "runtime_error")
        self.assertIn("MATLAB crashed", result["details"]["cause"])

    def test_verification_failed(self):
        eng = self._make_engine()
        # Track calls to get_param for the destination path
        destination = "my_model/Gain1"
        call_count = {"n": 0}

        original_get_param = eng.get_param

        def get_param_with_verify_fail(target, param, nargout=1):
            if target == destination and param == "Handle":
                call_count["n"] += 1
                # Precondition check (first call): raise — block doesn't exist yet
                # Verification check (second call): also raise — block never appeared
                raise RuntimeError("not found")
            return original_get_param(target, param, nargout=nargout)

        eng.get_param = get_param_with_verify_fail
        eng.add_block = lambda source, dest, nargout=0: None  # no-op add

        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "verification_failed")

    def test_rollback_payload_structure(self):
        result = self._run(self._default_args())
        rollback = result["rollback"]
        self.assertEqual(rollback["action"], "block_delete")
        self.assertEqual(rollback["destination"], "my_model/Gain1")
        self.assertFalse(rollback["available"])
        self.assertIn("not yet implemented", rollback["note"])

    def test_session_passes_to_rollback(self):
        result = self._run(self._default_args(session="my_session"))
        self.assertEqual(result["rollback"]["session"], "my_session")

    def test_session_absent_from_rollback_when_none(self):
        result = self._run(self._default_args(session=None))
        self.assertNotIn("session", result["rollback"])

    def test_connection_error_propagates(self):
        error_response = {
            "error": "engine_unavailable",
            "message": "No MATLAB session available.",
            "details": {},
        }
        with patch.object(
            block_cmd, "safe_connect_to_session", return_value=(None, error_response)
        ):
            result = block_cmd.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")


if __name__ == "__main__":
    unittest.main()
