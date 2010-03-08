import unittest
from hugin.haproxy.filters.slowestrequests import SlowestRequests

class TestSlowestRequests(unittest.TestCase):

    def setUp(self):
        self.filter = SlowestRequests()

    def test_slowest_empty(self):
        self.failUnlessEqual(self.filter.stats(), dict())

        self.filter.process(dict(url='/slow/1', Tr=4000)) # Below threshold
        self.failUnlessEqual(self.filter.stats(), dict())

    def test_slowest_basic(self):
        self.filter.process(dict(url='/slow/1', Tr=6000))
        expect = {'/slow/1':6000}
        self.failUnlessEqual(self.filter.stats(reset=False), expect)

        self.filter.process(dict(url='/slow/1', Tr=4000)) # Below threshold but added to average because url exists
        expect = {'/slow/1':6000}
        self.failUnlessEqual(self.filter.stats(reset=False), expect)
