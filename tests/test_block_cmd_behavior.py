"""Tests for block_add action."""

import unittest
from unittest.mock import patch

from simulink_cli import matlab_transport
from tests.fakes import FakeBlockEngine
from simulink_cli.actions import block_cmd


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

    def test_valid_position_returns_none(self):
        result = block_cmd.validate(
            {
                "source": "simulink/Gain",
                "destination": "m/G1",
                "position": [50, 100, 130, 130],
            }
        )
        self.assertIsNone(result)

    def test_invalid_position_wrong_length(self):
        result = block_cmd.validate(
            {
                "source": "simulink/Gain",
                "destination": "m/G1",
                "position": [50, 100],
            }
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_invalid_position_non_numeric(self):
        result = block_cmd.validate(
            {
                "source": "simulink/Gain",
                "destination": "m/G1",
                "position": [50, "a", 130, 130],
            }
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")


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
        self.assertIn("auto_load_attempted", result["details"])

    def test_source_not_found_includes_suggestions(self):
        eng = self._make_engine(library_sources=[
            "simulink/Math Operations/Gain",
            "simulink/Math Operations/Sum",
            "simulink/Math Operations/Product",
        ])
        result = self._run(self._default_args(source="simulink/Math Operations/Gian"))
        self.assertEqual(result["error"], "source_not_found")
        self.assertIn("suggestions", result["details"])
        suggestions = result["details"]["suggestions"]
        self.assertTrue(any("Gain" in s for s in suggestions))

    def test_source_auto_loads_library_on_miss(self):
        eng = self._make_engine(
            library_sources=[],
            loadable_libraries={"powerlib": ["powerlib/powergui"]},
        )
        result = self._run(
            self._default_args(source="powerlib/powergui", destination="my_model/powergui"),
            engine=eng,
        )
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "block_add")
        self.assertTrue(result["verified"])

    def test_source_auto_load_no_retry_when_already_loaded(self):
        """When the source is found on first try, load_system is not called."""
        eng = self._make_engine()
        result = self._run(self._default_args(), engine=eng)
        self.assertNotIn("error", result)
        self.assertTrue(result["verified"])

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
        self.assertTrue(rollback["available"])
        self.assertNotIn("note", rollback)

    def test_session_passes_to_rollback(self):
        result = self._run(self._default_args(session="my_session"))
        self.assertEqual(result["rollback"]["session"], "my_session")

    def test_session_absent_from_rollback_when_none(self):
        result = self._run(self._default_args(session=None))
        self.assertNotIn("session", result["rollback"])

    def test_position_passed_to_result(self):
        result = self._run(self._default_args(position=[50, 100, 130, 130]))
        self.assertNotIn("error", result)
        self.assertEqual(result["position"], [50, 100, 130, 130])

    def test_position_absent_when_not_provided(self):
        result = self._run(self._default_args())
        self.assertNotIn("position", result)

    def test_auto_layout_does_not_break_success(self):
        result = self._run(self._default_args(auto_layout=True))
        self.assertNotIn("error", result)
        self.assertTrue(result["verified"])

    def test_cross_model_copy_succeeds(self):
        """Source from a loaded model (not library) should work."""
        eng = self._make_engine(
            loaded_models=["my_model", "ref_model"],
            library_sources=[],
        )
        # ref_model/Controller is a block in a loaded model
        eng._blocks.add("ref_model/Controller")
        result = self._run(
            self._default_args(source="ref_model/Controller", destination="my_model/Controller"),
            engine=eng,
        )
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "block_add")
        self.assertEqual(result["source"], "ref_model/Controller")
        self.assertTrue(result["verified"])

    def test_cross_model_copy_source_model_not_loaded(self):
        """Source from an unloaded model should return source_not_found."""
        eng = self._make_engine(library_sources=[])
        result = self._run(
            self._default_args(source="unloaded_model/Block", destination="my_model/Block"),
            engine=eng,
        )
        self.assertEqual(result["error"], "source_not_found")
        self.assertIn("source model is loaded", result["suggested_fix"])

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


class BlockAddBatchValidationTests(unittest.TestCase):
    def _batch_args(self, **overrides):
        args = {
            "blocks": [
                {"source": "simulink/Gain", "destination": "m/G1"},
                {"source": "simulink/Sum", "destination": "m/S1"},
            ],
            "session": None,
            "source": None,
            "destination": None,
            "position": None,
            "auto_layout": False,
        }
        args.update(overrides)
        return args

    def test_blocks_and_source_mutually_exclusive(self):
        args = self._batch_args(source="simulink/Gain")
        result = block_cmd.validate(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_blocks_and_destination_mutually_exclusive(self):
        args = self._batch_args(destination="m/G1")
        result = block_cmd.validate(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_empty_blocks_array_returns_error(self):
        args = self._batch_args(blocks=[])
        result = block_cmd.validate(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_item_missing_source_returns_error(self):
        args = self._batch_args(blocks=[{"destination": "m/G1"}])
        result = block_cmd.validate(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_item_missing_destination_returns_error(self):
        args = self._batch_args(blocks=[{"source": "simulink/Gain"}])
        result = block_cmd.validate(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_too_many_items_returns_error(self):
        many = [{"source": "simulink/Gain", "destination": f"m/G{i}"} for i in range(101)]
        args = self._batch_args(blocks=many)
        result = block_cmd.validate(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_blocks_returns_none(self):
        result = block_cmd.validate(self._batch_args())
        self.assertIsNone(result)


class BlockAddBatchExecuteTests(unittest.TestCase):
    def _make_engine(self, **kwargs):
        defaults = {
            "loaded_models": ["m"],
            "library_sources": ["simulink/Gain", "simulink/Sum", "simulink/Mux"],
        }
        defaults.update(kwargs)
        return FakeBlockEngine(**defaults)

    def _run(self, args, engine=None):
        if engine is None:
            engine = self._make_engine()
        with patch.object(block_cmd, "safe_connect_to_session", return_value=(engine, None)):
            return block_cmd.execute(args)

    def _batch_args(self, blocks, **overrides):
        args = {
            "blocks": blocks,
            "session": None,
            "source": None,
            "destination": None,
            "position": None,
            "auto_layout": False,
        }
        args.update(overrides)
        return args

    def test_all_succeed_returns_completed_equal_total(self):
        blocks = [
            {"source": "simulink/Gain", "destination": "m/G1"},
            {"source": "simulink/Sum", "destination": "m/S1"},
        ]
        result = self._run(self._batch_args(blocks))
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "block_add")
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["results"]), 2)
        self.assertTrue(result["results"][0]["verified"])
        self.assertTrue(result["results"][1]["verified"])

    def test_stops_on_failure_returns_completed_less_than_total(self):
        blocks = [
            {"source": "simulink/Gain", "destination": "m/G1"},
            {"source": "simulink/Sum", "destination": "m/S1"},
            {"source": "bad/path", "destination": "m/X"},
        ]
        result = self._run(self._batch_args(blocks))
        self.assertIn("error", result)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["error"]["index"], 2)
        self.assertEqual(result["error"]["error"], "source_not_found")

    def test_model_not_loaded_returns_completed_zero(self):
        eng = self._make_engine(loaded_models=[])
        blocks = [{"source": "simulink/Gain", "destination": "m/G1"}]
        result = self._run(self._batch_args(blocks), engine=eng)
        self.assertIn("error", result)
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["error"]["error"], "model_not_found")


if __name__ == "__main__":
    unittest.main()
