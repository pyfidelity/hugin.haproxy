import unittest

class TestMuninResults(unittest.TestCase):

    def setUp(self):
        pass

    def test_fail(self):
        self.failUnless(True, "Tests run!")
