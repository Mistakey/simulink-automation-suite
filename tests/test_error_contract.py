import unittest

from skills.simulink_scan.scripts.sl_errors import make_error


class ErrorContractTests(unittest.TestCase):
    def test_make_error_has_stable_shape(self):
        payload = make_error("model_not_found", "Model not opened")
        self.assertEqual(payload["error"], "model_not_found")
        self.assertEqual(payload["message"], "Model not opened")
        self.assertIn("details", payload)
        self.assertEqual(payload["details"], {})

    def test_make_error_accepts_details_and_suggested_fix(self):
        payload = make_error(
            "session_required",
            "Multiple sessions found",
            details={"sessions": ["MATLAB_A", "MATLAB_B"]},
            suggested_fix="Run session list and pass --session.",
        )
        self.assertEqual(payload["error"], "session_required")
        self.assertEqual(payload["details"]["sessions"], ["MATLAB_A", "MATLAB_B"])
        self.assertEqual(
            payload["suggested_fix"],
            "Run session list and pass --session.",
        )


if __name__ == "__main__":
    unittest.main()
