import unittest
from simulink_cli import matlab_transport
from tests.fakes import FakeLineEngine


class TransportLineTests(unittest.TestCase):
    def test_add_line_function_exists(self):
        self.assertTrue(callable(matlab_transport.add_line))

    def test_close_system_function_exists(self):
        self.assertTrue(callable(matlab_transport.close_system))

    def test_update_diagram_function_exists(self):
        self.assertTrue(callable(matlab_transport.update_diagram))


class FakeLineEngineTests(unittest.TestCase):
    def _make_engine(self):
        return FakeLineEngine(
            loaded_models=["m"],
            blocks=["m/A", "m/B"],
            library_sources=["simulink/Gain"],
        )

    def test_add_line_creates_line(self):
        eng = self._make_engine()
        handle = eng.add_line("m", "A/1", "B/1", nargout=1)
        self.assertIsInstance(handle, float)

    def test_add_line_duplicate_dst_port_raises(self):
        eng = self._make_engine()
        eng.add_line("m", "A/1", "B/1", nargout=1)
        with self.assertRaises(RuntimeError):
            eng.add_line("m", "A/1", "B/1", nargout=1)

    def test_add_line_model_not_loaded_raises(self):
        eng = FakeLineEngine()
        with self.assertRaises(RuntimeError):
            eng.add_line("missing", "A/1", "B/1", nargout=1)

    def test_add_line_block_not_found_raises(self):
        eng = FakeLineEngine(loaded_models=["m"])
        with self.assertRaises(RuntimeError):
            eng.add_line("m", "NoBlock/1", "B/1", nargout=1)

    def test_get_param_line_handle(self):
        eng = self._make_engine()
        handle = eng.add_line("m", "A/1", "B/1", nargout=1)
        result = eng.get_param(handle, "Handle", nargout=1)
        self.assertEqual(result, handle)

    def test_get_param_invalid_handle_raises(self):
        eng = self._make_engine()
        with self.assertRaises(RuntimeError):
            eng.get_param(999.999, "Handle", nargout=1)


from unittest.mock import patch
from simulink_cli.actions import line_add


class LineAddValidationTests(unittest.TestCase):
    def _default_args(self, **overrides):
        args = {
            "model": "m", "src_block": "A", "src_port": 1,
            "dst_block": "B", "dst_port": 1, "session": None,
        }
        args.update(overrides)
        return args

    def test_missing_model_returns_error(self):
        result = line_add.validate(self._default_args(model=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_src_block_returns_error(self):
        result = line_add.validate(self._default_args(src_block=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_dst_block_returns_error(self):
        result = line_add.validate(self._default_args(dst_block=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_src_block_with_slash_returns_error(self):
        result = line_add.validate(self._default_args(src_block="A/B"))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_dst_block_with_slash_returns_error(self):
        result = line_add.validate(self._default_args(dst_block="A/B"))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_src_port_returns_error(self):
        result = line_add.validate(self._default_args(src_port=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_dst_port_returns_error(self):
        result = line_add.validate(self._default_args(dst_port=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_non_positive_src_port_returns_error(self):
        result = line_add.validate(self._default_args(src_port=0))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_non_positive_dst_port_returns_error(self):
        result = line_add.validate(self._default_args(dst_port=-1))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_args_returns_none(self):
        result = line_add.validate(self._default_args())
        self.assertIsNone(result)


class LineAddExecuteTests(unittest.TestCase):
    def _make_engine(self, **kwargs):
        defaults = {
            "loaded_models": ["m"],
            "blocks": ["m/A", "m/B"],
            "library_sources": ["simulink/Gain"],
        }
        defaults.update(kwargs)
        return FakeLineEngine(**defaults)

    def _run(self, args, engine=None):
        if engine is None:
            engine = self._make_engine()
        with patch.object(line_add, "safe_connect_to_session", return_value=(engine, None)):
            return line_add.execute(args)

    def _default_args(self, **overrides):
        args = {
            "model": "m", "src_block": "A", "src_port": 1,
            "dst_block": "B", "dst_port": 1, "session": None,
        }
        args.update(overrides)
        return args

    def test_adds_line_successfully(self):
        result = self._run(self._default_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "line_add")
        self.assertEqual(result["model"], "m")
        self.assertIsInstance(result["line_handle"], float)
        self.assertTrue(result["verified"])

    def test_model_not_found_returns_error(self):
        eng = self._make_engine(loaded_models=[])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_not_found")

    def test_src_block_not_found_returns_error(self):
        eng = self._make_engine(blocks=["m/B"])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "block_not_found")
        self.assertEqual(result["details"]["role"], "source")

    def test_dst_block_not_found_returns_error(self):
        eng = self._make_engine(blocks=["m/A"])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "block_not_found")
        self.assertEqual(result["details"]["role"], "destination")

    def test_line_already_exists_returns_error(self):
        eng = self._make_engine()
        eng.add_line("m", "A/1", "B/1", nargout=1)  # pre-create
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "line_already_exists")

    def test_port_not_found_returns_error(self):
        eng = self._make_engine()
        from simulink_cli import matlab_transport
        with patch.object(
            matlab_transport, "add_line",
            side_effect=RuntimeError("Invalid port number: port not found"),
        ):
            result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "port_not_found")

    def test_runtime_error_on_add_line_failure(self):
        eng = self._make_engine()
        from simulink_cli import matlab_transport
        with patch.object(
            matlab_transport, "add_line",
            side_effect=RuntimeError("MATLAB crashed"),
        ):
            result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "runtime_error")
        self.assertIn("MATLAB crashed", result["details"]["cause"])

    def test_verification_failed(self):
        eng = self._make_engine()
        from simulink_cli import matlab_transport
        real_add_line = matlab_transport.add_line
        def add_line_then_break_verify(engine, system, src, dst):
            result = real_add_line(engine, system, src, dst)
            handle = result["value"]
            del engine._lines[handle]
            return result
        with patch.object(matlab_transport, "add_line", side_effect=add_line_then_break_verify):
            result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "verification_failed")
        self.assertEqual(result["details"]["write_state"], "attempted")

    def test_rollback_payload_structure(self):
        result = self._run(self._default_args())
        rollback = result["rollback"]
        self.assertEqual(rollback["action"], "line_delete")
        self.assertEqual(rollback["model"], "m")
        self.assertIn("line_handle", rollback)
        self.assertFalse(rollback["available"])
        self.assertIn("line_delete", rollback["note"])

    def test_session_passes_to_rollback(self):
        result = self._run(self._default_args(session="my_session"))
        self.assertEqual(result["rollback"]["session"], "my_session")

    def test_session_absent_from_rollback_when_none(self):
        result = self._run(self._default_args(session=None))
        self.assertNotIn("session", result["rollback"])

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(line_add, "safe_connect_to_session", return_value=(None, error_response)):
            result = line_add.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")


if __name__ == "__main__":
    unittest.main()
