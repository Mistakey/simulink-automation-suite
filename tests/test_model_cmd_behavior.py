"""Tests for model_new, model_open, model_save actions."""

import unittest
from unittest.mock import patch

from tests.fakes import FakeModelEngine
from simulink_cli.actions import model_new


def _model_new_args(name="test_model", session=None):
    return {"name": name, "session": session}


class ModelNewValidationTests(unittest.TestCase):
    def test_missing_name_returns_invalid_input(self):
        result = model_new.validate({"name": None, "session": None})
        self.assertEqual(result["error"], "invalid_input")

    def test_empty_name_returns_invalid_input(self):
        result = model_new.validate({"name": "", "session": None})
        self.assertIsNotNone(result)

    def test_valid_args_returns_none(self):
        result = model_new.validate(_model_new_args())
        self.assertIsNone(result)


class ModelNewExecuteTests(unittest.TestCase):
    def _make_engine(self, **kwargs):
        return FakeModelEngine(**kwargs)

    def test_creates_new_model(self):
        eng = self._make_engine()
        with patch.object(model_new, "safe_connect_to_session", return_value=(eng, None)):
            result = model_new.execute(_model_new_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "model_new")
        self.assertEqual(result["name"], "test_model")
        self.assertTrue(result["verified"])

    def test_returns_rollback_payload(self):
        eng = self._make_engine()
        with patch.object(model_new, "safe_connect_to_session", return_value=(eng, None)):
            result = model_new.execute(_model_new_args())
        self.assertIn("rollback", result)
        self.assertFalse(result["rollback"]["available"])

    def test_already_loaded_returns_error(self):
        eng = self._make_engine(loaded_models=["test_model"])
        with patch.object(model_new, "safe_connect_to_session", return_value=(eng, None)):
            result = model_new.execute(_model_new_args())
        self.assertEqual(result["error"], "model_already_loaded")

    def test_session_error_propagated(self):
        err = {"error": "no_session", "message": "No session", "details": {}}
        with patch.object(model_new, "safe_connect_to_session", return_value=(None, err)):
            result = model_new.execute(_model_new_args())
        self.assertEqual(result["error"], "no_session")
