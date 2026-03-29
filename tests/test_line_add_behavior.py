import unittest
from unittest.mock import patch
from tests.fakes import FakeLineEngine
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

    def test_string_src_port_valid(self):
        result = line_add.validate(self._default_args(src_port="RConn1"))
        self.assertIsNone(result)

    def test_string_dst_port_valid(self):
        result = line_add.validate(self._default_args(dst_port="LConn1"))
        self.assertIsNone(result)

    def test_empty_string_src_port_returns_error(self):
        result = line_add.validate(self._default_args(src_port=""))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_bool_src_port_returns_error(self):
        result = line_add.validate(self._default_args(src_port=True))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")


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
        self.assertEqual(rollback["src_block"], "A")
        self.assertEqual(rollback["src_port"], 1)
        self.assertEqual(rollback["dst_block"], "B")
        self.assertEqual(rollback["dst_port"], 1)
        self.assertTrue(rollback["available"])
        self.assertNotIn("line_handle", rollback)
        self.assertNotIn("note", rollback)

    def test_session_passes_to_rollback(self):
        result = self._run(self._default_args(session="my_session"))
        self.assertEqual(result["rollback"]["session"], "my_session")

    def test_session_absent_from_rollback_when_none(self):
        result = self._run(self._default_args(session=None))
        self.assertNotIn("session", result["rollback"])

    def test_adds_line_with_string_ports(self):
        result = self._run(self._default_args(src_port="RConn1", dst_port="LConn1"))
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "line_add")
        self.assertTrue(result["verified"])

    def test_rollback_preserves_string_port(self):
        result = self._run(self._default_args(src_port="RConn1", dst_port="LConn1"))
        rollback = result["rollback"]
        self.assertEqual(rollback["src_port"], "RConn1")
        self.assertEqual(rollback["dst_port"], "LConn1")

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(line_add, "safe_connect_to_session", return_value=(None, error_response)):
            result = line_add.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")


if __name__ == "__main__":
    unittest.main()
