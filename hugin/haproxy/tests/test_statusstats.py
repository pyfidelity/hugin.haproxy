import unittest
from hugin.haproxy.filters.statusstats import StatusStats, LOGSTATUSCODES

class TestStatusStats(unittest.TestCase):

    def setUp(self):
        self.filter = StatusStats()

    def test_statusalarm_ok(self):
        self.filter.process(dict(status=200))
        self.failUnlessEqual(self.filter.stats(), dict.fromkeys(LOGSTATUSCODES, 0))

    def test_statusalarm_errors(self):
        empty = dict.fromkeys(LOGSTATUSCODES, 0)
        for status in ['401', '403', '404', '500', '501', '502', '503', '504']:
            self.filter.process(dict(status=status))
            expect = empty.copy()
            expect[status]=1
            self.failUnlessEqual(self.filter.stats(), expect)

    def test_statusalarm_multierrors(self):
        for status in ['401', '200', '403', '404', '401', '204', '404', '404']:
            self.filter.process(dict(status=status))

        expect = dict.fromkeys(LOGSTATUSCODES, 0)
        expect.update({'401':2, '403':1, '404':3})
        self.failUnlessEqual(self.filter.stats(), expect)
