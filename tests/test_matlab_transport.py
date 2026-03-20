import unittest

from tests.fakes import OutputSensitiveEngine
from simulink_cli import matlab_transport


class TypeErrorAfterSideEffectEngine:
    def __init__(self):
        self.calls = []

    def set_param(self, target, param, value, nargout=1):
        self.calls.append((target, param, value, nargout))
        if nargout == 0:
            raise TypeError("internal failure after side effect")
        return None


class LastwarnAndWarningLogEngine:
    def __init__(self):
        self.lastwarn_calls = []
        self.warning_log = ["fallback warning"]
        self._responses = [("lastwarn message", "id"), ("", "")]

    def find_system(self, *args, nargout=1):
        return ["m"]

    def lastwarn(self, *args, **kwargs):
        self.lastwarn_calls.append((args, kwargs))
        if args == ("", "") and kwargs == {"nargout": 0}:
            return None
        if kwargs == {"nargout": 2}:
            return self._responses.pop(0)
        raise TypeError("unsupported")


class BdrootOutputSensitiveEngine(OutputSensitiveEngine):
    def bdroot(self, *, nargout):
        self.calls.append(("bdroot", nargout))
        return self.current_root


class MatlabFuncLike:
    def __call__(self, *args, **kwargs):
        raise TypeError("unsupported")


class DynamicAttributeEngine:
    def find_system(self, *args, nargout=1):
        return []

    def lastwarn(self, *args, **kwargs):
        if args == ("", "") and kwargs == {"nargout": 0}:
            return None
        if kwargs == {"nargout": 2}:
            return ("", "")
        raise TypeError("unsupported")

    def __getattr__(self, name):
        return MatlabFuncLike()


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

    def test_call_no_output_does_not_retry_on_internal_typeerror(self):
        eng = TypeErrorAfterSideEffectEngine()
        with self.assertRaises(TypeError):
            matlab_transport.call_no_output(eng, "set_param", "m/Gain", "Gain", "2.0")
        self.assertEqual(eng.calls, [("m/Gain", "Gain", "2.0", 0)])

    def test_warning_drain_prefers_lastwarn_and_clears_fallback_state(self):
        eng = LastwarnAndWarningLogEngine()

        first = matlab_transport.find_system(eng, "m", "Type", "block")
        second = matlab_transport.find_system(eng, "m", "Type", "block")

        self.assertEqual(first["warnings"], ["lastwarn message"])
        self.assertEqual(second["warnings"], [])
        self.assertEqual(eng.warning_log, [])

    def test_bdroot_fallback_is_transport_backed(self):
        eng = BdrootOutputSensitiveEngine()
        eng.open_models = []
        eng.current_root = "m"
        result = matlab_transport.bdroot(eng)
        self.assertEqual(result["value"], "m")

    def test_warning_drain_ignores_dynamic_non_log_attribute(self):
        eng = DynamicAttributeEngine()
        result = matlab_transport.find_system(eng, "Type", "block_diagram")
        self.assertEqual(result["value"], [])
        self.assertEqual(result["warnings"], [])
