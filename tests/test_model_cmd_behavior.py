"""Tests for model_new, model_open, model_save actions."""

import unittest
from unittest.mock import patch

from tests.fakes import FakeModelEngine
from simulink_cli.actions import model_new
from simulink_cli.actions import model_open
from simulink_cli.actions import model_save


class ModelNewTests(unittest.TestCase):
    def test_creates_new_model(self):
        eng = FakeModelEngine()
        with patch.object(model_new, "safe_connect_to_session", return_value=(eng, None)):
            result = model_new.execute({"name": "test_model", "session": None})
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "model_new")
        self.assertTrue(result["verified"])

    def test_rollback_activated_with_model_close(self):
        eng = FakeModelEngine()
        with patch.object(model_new, "safe_connect_to_session", return_value=(eng, None)):
            result = model_new.execute({"name": "test_model", "session": None})
        rollback = result["rollback"]
        self.assertTrue(rollback["available"])
        self.assertEqual(rollback["action"], "model_close")
        self.assertEqual(rollback["model"], "test_model")
        self.assertTrue(rollback["force"])

    def test_already_loaded_returns_error(self):
        eng = FakeModelEngine(loaded_models=["test_model"])
        with patch.object(model_new, "safe_connect_to_session", return_value=(eng, None)):
            result = model_new.execute({"name": "test_model", "session": None})
        self.assertEqual(result["error"], "model_already_loaded")


class ModelOpenTests(unittest.TestCase):
    def test_opens_existing_file(self):
        eng = FakeModelEngine(filesystem=["C:/models/test_model.slx"])
        with patch.object(model_open, "safe_connect_to_session", return_value=(eng, None)):
            result = model_open.execute({"path": "C:/models/test_model.slx", "session": None})
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "model_open")

    def test_already_open_model_succeeds_idempotent(self):
        eng = FakeModelEngine(loaded_models=["test_model"], filesystem=["C:/models/test_model.slx"])
        with patch.object(model_open, "safe_connect_to_session", return_value=(eng, None)):
            result = model_open.execute({"path": "C:/models/test_model.slx", "session": None})
        self.assertNotIn("error", result)

    def test_file_not_found_returns_error(self):
        eng = FakeModelEngine()
        with patch.object(model_open, "safe_connect_to_session", return_value=(eng, None)):
            result = model_open.execute({"path": "C:/missing.slx", "session": None})
        self.assertEqual(result["error"], "model_not_found")


class ModelSaveTests(unittest.TestCase):
    def test_saves_loaded_model(self):
        eng = FakeModelEngine(loaded_models=["test_model"])
        with patch.object(model_save, "safe_connect_to_session", return_value=(eng, None)):
            result = model_save.execute({"model": "test_model", "session": None})
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "model_save")

    def test_model_not_loaded_returns_error(self):
        eng = FakeModelEngine()
        with patch.object(model_save, "safe_connect_to_session", return_value=(eng, None)):
            result = model_save.execute({"model": "test_model", "session": None})
        self.assertEqual(result["error"], "model_not_found")


if __name__ == "__main__":
    unittest.main()
