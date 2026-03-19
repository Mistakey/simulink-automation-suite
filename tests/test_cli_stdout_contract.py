import io
import json
import unittest
from unittest.mock import patch

from simulink_cli.core import main
from tests.fakes import FakeScanEngine


class OutputSensitiveScanEngine(FakeScanEngine):
    def __init__(self):
        super().__init__(
            models=["m"],
            active_root="m",
            shallow_blocks={"m": ["m", "m/Gain"]},
            recursive_blocks={"m": ["m", "m/Gain"]},
            block_types={"m": "SubSystem", "m/Gain": "Gain"},
            valid_handles={"m", "m/Gain"},
        )
        self.warning_log = []

    def find_system(self, *args):
        self.warning_log.append("Variant warning")
        return super().find_system(*args)


class CliStdoutContractTests(unittest.TestCase):
    def test_main_emits_single_json_payload_when_action_has_warnings(self):
        buf = io.StringIO()
        eng = OutputSensitiveScanEngine()
        with patch("simulink_cli.actions.scan.safe_connect_to_session", return_value=(eng, None)):
            with patch("sys.stdout", buf):
                exit_code = main(["scan", "--model", "m"])
        raw = buf.getvalue()
        payload = json.loads(raw)
        self.assertEqual(exit_code, 0)
        self.assertIn("warnings", payload)
        self.assertEqual(raw.strip(), json.dumps(payload, ensure_ascii=True, default=str))


if __name__ == "__main__":
    unittest.main()
