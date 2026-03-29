import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from simulink_cli.core import build_parser, main, parse_json_request


class JsonInputModeTests(unittest.TestCase):
    """Unified JSON input mode tests — covers scan + edit JSON parsing."""

    # -- build_parser flag exposure --------------------------------------------

    def test_build_parser_exposes_json_flag(self):
        parser = build_parser()
        option_strings = []
        for action in parser._actions:
            option_strings.extend(action.option_strings)
        self.assertIn("--json", option_strings)

    # -- Valid scan/read requests via parse_json_request ------------------------

    def test_parse_json_scan_request(self):
        action, args = parse_json_request(
            '{"action":"scan","model":"demo","recursive":true}'
        )
        self.assertEqual(action, "scan")
        self.assertEqual(args["model"], "demo")
        self.assertTrue(args["recursive"])

    def test_parse_json_connections_request(self):
        action, args = parse_json_request(
            '{"action":"connections","target":"m1/Gain","direction":"both",'
            '"depth":1,"detail":"summary","max_edges":20,'
            '"fields":["target","edges"]}'
        )
        self.assertEqual(action, "connections")
        self.assertEqual(args["target"], "m1/Gain")
        self.assertEqual(args["direction"], "both")
        self.assertEqual(args["depth"], 1)
        self.assertEqual(args["detail"], "summary")
        self.assertEqual(args["max_edges"], 20)
        # NEW API: fields stays as list, not comma-joined string
        self.assertEqual(args["fields"], ["target", "edges"])

    def test_parse_json_find_request(self):
        action, args = parse_json_request(
            '{"action":"find","model":"my_model","name":"PID",'
            '"block_type":"SubSystem","max_results":50,'
            '"fields":["path","type"]}'
        )
        self.assertEqual(action, "find")
        self.assertEqual(args["model"], "my_model")
        self.assertEqual(args["name"], "PID")
        self.assertEqual(args["block_type"], "SubSystem")
        self.assertEqual(args["max_results"], 50)
        # NEW API: fields stays as list, not comma-joined string
        self.assertEqual(args["fields"], ["path", "type"])

    def test_parse_json_schema_request(self):
        action, args = parse_json_request('{"action":"schema"}')
        self.assertEqual(action, "schema")
        self.assertEqual(args, {})

    # -- Valid edit requests via parse_json_request -----------------------------

    def test_parse_json_set_param_request(self):
        action, args = parse_json_request(
            '{"action":"set_param","target":"m/Gain1",'
            '"param":"Gain","value":"2.0","dry_run":true}'
        )
        self.assertEqual(action, "set_param")
        self.assertEqual(args["target"], "m/Gain1")
        self.assertEqual(args["param"], "Gain")
        self.assertEqual(args["value"], "2.0")

    def test_parse_json_set_param_with_expected_current_value(self):
        action, args = parse_json_request(
            '{"action":"set_param","target":"m/Gain1","param":"Gain","value":"2.0",'
            '"dry_run":false,"expected_current_value":"1.5"}'
        )
        self.assertEqual(action, "set_param")
        self.assertEqual(args["expected_current_value"], "1.5")

    # -- Rejection: invalid JSON payload ---------------------------------------

    def test_rejects_invalid_json_payload(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request("{invalid-json")
        self.assertIn("invalid_json", str(ctx.exception))

    # -- Rejection: missing action field ---------------------------------------

    def test_rejects_missing_action_field(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"model":"demo"}')
        self.assertIn("action", str(ctx.exception))

    # -- Rejection: unknown field ----------------------------------------------

    def test_rejects_unknown_json_field_for_scan(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request(
                '{"action":"scan","model":"demo","unknown":"x"}'
            )
        self.assertIn("unknown_parameter", str(ctx.exception))

    def test_rejects_unknown_json_field_for_schema(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"schema","bogus":"x"}')
        self.assertIn("unknown_parameter", str(ctx.exception))

    def test_rejects_unknown_json_field_for_set_param(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request(
                '{"action":"set_param","target":"m/B",'
                '"param":"P","value":"1","bogus":"x"}'
            )
        self.assertIn("unknown_parameter", str(ctx.exception))

    # -- Rejection: type mismatches --------------------------------------------

    def test_rejects_wrong_type_string_field_as_int(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"scan","model":123}')
        self.assertIn("invalid_json", str(ctx.exception))

    def test_rejects_wrong_type_boolean_field_as_string(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request(
                '{"action":"connections","target":"m1/Gain",'
                '"include_handles":"yes"}'
            )
        self.assertIn("invalid_json", str(ctx.exception))

    def test_rejects_wrong_type_string_value_as_int(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request(
                '{"action":"set_param","target":"m/B",'
                '"param":"P","value":123}'
            )
        self.assertIn("invalid_json", str(ctx.exception))

    # -- Mixed mode (json + flags) — uses main() for argv handling -------------

    def test_rejects_mixed_json_and_flags_scan(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main([
                "scan", "--model", "demo",
                "--json", '{"action":"scan","model":"demo"}',
            ])
        self.assertEqual(code, 1)
        output = json.loads(buf.getvalue())
        self.assertEqual(output["error"], "json_conflict")

    # -- Port type fields (line_add) -------------------------------------------

    def test_parse_json_line_add_with_string_port(self):
        action, args = parse_json_request(
            '{"action":"line_add","model":"m","src_block":"A","src_port":"RConn1",'
            '"dst_block":"B","dst_port":"LConn1"}'
        )
        self.assertEqual(action, "line_add")
        self.assertEqual(args["src_port"], "RConn1")
        self.assertEqual(args["dst_port"], "LConn1")

    def test_parse_json_line_add_integer_port_still_works(self):
        action, args = parse_json_request(
            '{"action":"line_add","model":"m","src_block":"A","src_port":1,'
            '"dst_block":"B","dst_port":1}'
        )
        self.assertEqual(args["src_port"], 1)
        self.assertEqual(args["dst_port"], 1)

    def test_parse_json_line_add_rejects_float_port(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request(
                '{"action":"line_add","model":"m","src_block":"A","src_port":1.5,'
                '"dst_block":"B","dst_port":1}'
            )
        self.assertIn("invalid_json", str(ctx.exception))

    def test_rejects_mixed_json_and_flags_set_param(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main([
                "set_param", "--target", "m/B",
                "--json",
                '{"action":"set_param","target":"m/B","param":"P","value":"1"}',
            ])
        self.assertEqual(code, 1)
        output = json.loads(buf.getvalue())
        self.assertEqual(output["error"], "json_conflict")

    def test_parse_json_set_param_multi_request(self):
        action, args = parse_json_request(
            '{"action":"set_param","target":"m/B",'
            '"params":{"rep_seq_t":"[0 5e-5 1e-4]","rep_seq_y":"[-1 1 -1]"}}'
        )
        self.assertEqual(action, "set_param")
        self.assertEqual(args["params"]["rep_seq_t"], "[0 5e-5 1e-4]")
        self.assertIsNone(args["param"])

    def test_parse_json_set_param_multi_with_expected_current_values(self):
        action, args = parse_json_request(
            '{"action":"set_param","target":"m/B",'
            '"params":{"Gain":"2.0"},"dry_run":false,'
            '"expected_current_values":{"Gain":"1.5"}}'
        )
        self.assertEqual(args["expected_current_values"]["Gain"], "1.5")

    def test_parse_json_set_param_rejects_params_as_list(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request(
                '{"action":"set_param","target":"m/B","params":["Gain","2.0"]}'
            )
        self.assertIn("invalid_json", str(ctx.exception))

    # -- --json-file mode ---------------------------------------------------------

    def test_json_file_mode_reads_payload_from_file(self):
        payload = '{"action":"schema"}'
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write(payload)
            f.flush()
            path = f.name
        try:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = main(["--json-file", path])
            self.assertEqual(code, 0)
            output = json.loads(buf.getvalue())
            self.assertIn("actions", output)
        finally:
            os.unlink(path)

    def test_json_file_mode_rejects_missing_file(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--json-file", "/nonexistent/path.json"])
        self.assertEqual(code, 1)
        output = json.loads(buf.getvalue())
        self.assertEqual(output["error"], "invalid_input")

    def test_json_file_mode_rejects_mixed_with_json(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--json", '{"action":"schema"}', "--json-file", "f.json"])
        self.assertEqual(code, 1)
        output = json.loads(buf.getvalue())
        self.assertEqual(output["error"], "json_conflict")

    def test_json_file_mode_rejects_mixed_with_flags(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"action":"schema"}')
            f.flush()
            path = f.name
        try:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = main(["scan", "--json-file", path])
            self.assertEqual(code, 1)
            output = json.loads(buf.getvalue())
            self.assertEqual(output["error"], "json_conflict")
        finally:
            os.unlink(path)

    def test_parse_json_block_add_batch(self):
        action, args = parse_json_request(
            '{"action":"block_add","blocks":[{"source":"simulink/Gain","destination":"m/G1"}]}'
        )
        self.assertEqual(action, "block_add")
        self.assertIsInstance(args["blocks"], list)
        self.assertIsNone(args["source"])

    def test_parse_json_line_add_batch(self):
        action, args = parse_json_request(
            '{"action":"line_add","model":"m","lines":[{"src_block":"A","src_port":1,"dst_block":"B","dst_port":1}]}'
        )
        self.assertEqual(action, "line_add")
        self.assertIsInstance(args["lines"], list)
        self.assertIsNone(args["src_block"])


if __name__ == "__main__":
    unittest.main()
