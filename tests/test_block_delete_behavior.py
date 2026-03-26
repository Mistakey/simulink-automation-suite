"""Tests for block_delete action."""

import unittest
from unittest.mock import patch
from tests.fakes import FakeBlockEngine
from simulink_cli.actions import block_delete


class BlockDeleteValidationTests(unittest.TestCase):
    def test_missing_destination_returns_error(self):
        result = block_delete.validate({})
        self.assertIsNotNone(result)
        self.assertIn("error", result)

    def test_empty_destination_returns_error(self):
        result = block_delete.validate({"destination": ""})
        self.assertIsNotNone(result)
        self.assertIn("error", result)

    def test_valid_args_returns_none(self):
        result = block_delete.validate({"destination": "m/Gain1"})
        self.assertIsNone(result)


class BlockDeleteExecuteTests(unittest.TestCase):
    def _make_engine(self, loaded_models=None, blocks=None):
        return FakeBlockEngine(
            loaded_models=loaded_models if loaded_models is not None else ["m"],
            blocks=blocks if blocks is not None else ["m/Gain1"],
        )

    def _run(self, args, engine):
        with patch(
            "simulink_cli.actions.block_delete.safe_connect_to_session",
            return_value=(engine, None),
        ):
            return block_delete.execute(args)

    def test_deletes_block_successfully(self):
        eng = self._make_engine()
        result = self._run({"destination": "m/Gain1"}, eng)
        self.assertEqual(result["action"], "block_delete")
        self.assertEqual(result["destination"], "m/Gain1")
        self.assertTrue(result["verified"])

    def test_model_not_found_returns_error(self):
        eng = self._make_engine(loaded_models=[], blocks=[])
        result = self._run({"destination": "missing_model/Gain1"}, eng)
        self.assertEqual(result["error"], "model_not_found")
        self.assertIn("suggested_fix", result)

    def test_block_not_found_returns_error(self):
        eng = self._make_engine(loaded_models=["m"], blocks=[])
        result = self._run({"destination": "m/NoBlock"}, eng)
        self.assertEqual(result["error"], "block_not_found")
        self.assertIn("suggested_fix", result)

    def test_verification_failed_when_block_still_exists(self):
        eng = self._make_engine()
        # Patch delete_block as a no-op so the block persists in the fake engine
        with patch(
            "simulink_cli.actions.block_delete.safe_connect_to_session",
            return_value=(eng, None),
        ):
            with patch.object(eng, "delete_block"):  # no-op: block stays
                result = block_delete.execute({"destination": "m/Gain1"})
        self.assertEqual(result["error"], "verification_failed")

    def test_runtime_error_on_delete_failure(self):
        eng = self._make_engine()
        with patch(
            "simulink_cli.actions.block_delete.safe_connect_to_session",
            return_value=(eng, None),
        ):
            with patch.object(
                eng, "delete_block", side_effect=RuntimeError("delete failed")
            ):
                result = block_delete.execute({"destination": "m/Gain1"})
        self.assertEqual(result["error"], "runtime_error")

    def test_rollback_not_available(self):
        eng = self._make_engine()
        result = self._run({"destination": "m/Gain1"}, eng)
        self.assertFalse(result["rollback"]["available"])
        self.assertIn("note", result["rollback"])

    def test_session_passes_to_rollback(self):
        eng = self._make_engine()
        result = self._run({"destination": "m/Gain1", "session": "mysession"}, eng)
        self.assertEqual(result["rollback"]["session"], "mysession")

    def test_session_absent_from_rollback_when_none(self):
        eng = self._make_engine()
        result = self._run({"destination": "m/Gain1"}, eng)
        self.assertNotIn("session", result["rollback"])

    def test_connection_error_propagates(self):
        error = {"error": "engine_unavailable", "message": "no engine"}
        with patch(
            "simulink_cli.actions.block_delete.safe_connect_to_session",
            return_value=(None, error),
        ):
            result = block_delete.execute({"destination": "m/Gain1"})
        self.assertEqual(result["error"], "engine_unavailable")


if __name__ == "__main__":
    unittest.main()
