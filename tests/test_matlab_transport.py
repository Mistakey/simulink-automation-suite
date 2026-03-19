import unittest

from tests.fakes import OutputSensitiveEngine
from simulink_cli import matlab_transport


class MatlabTransportTests(unittest.TestCase):
    def test_call_no_output_forces_nargout_zero(self):
        eng = OutputSensitiveEngine()
        matlab_transport.call_no_output(eng, "set_param", "m/Gain", "Gain", "2.0")
        self.assertIn(("set_param", "m/Gain", "Gain", "2.0", 0), eng.calls)

    def test_find_system_wrapper_returns_post_call_warning_list(self):
        eng = OutputSensitiveEngine()
        result = matlab_transport.find_system(eng, "m", "Type", "block")
        self.assertEqual(result["value"], ["m", "m/Gain"])
        self.assertEqual(result["warnings"], ["Variant warning"])

    def test_set_param_round_trips_complex_strings_unchanged(self):
        eng = OutputSensitiveEngine()
        matlab_transport.set_param(eng, "m/Sub\nSystem", "FormatString", "%.3f\nnext")
        self.assertIn(("set_param", "m/Sub\nSystem", "FormatString", "%.3f\nnext", 0), eng.calls)
