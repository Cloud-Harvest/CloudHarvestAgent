import unittest

"""
These tests should always pass and verify that python and testing is working as expected.
"""


class TestSuite(unittest.TestCase):
    def test_case1(self):
        self.assertEqual(1, 1)

    def test_case2(self):
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
