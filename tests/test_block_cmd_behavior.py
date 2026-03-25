"""Tests for block_add action."""

import unittest

from simulink_cli import matlab_transport


class TransportAddBlockTests(unittest.TestCase):
    def test_add_block_function_exists(self):
        self.assertTrue(callable(matlab_transport.add_block))


if __name__ == "__main__":
    unittest.main()
