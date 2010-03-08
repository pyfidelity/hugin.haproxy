import unittest
from hugin.haproxy.filters.statusalarm import ServiceUnavailable
from time import time

class TestStatusAlarm(unittest.TestCase):

    def setUp(self):
        self.filter = ServiceUnavailable()

    def test_statusalarm_backends(self):
        self.filter.process(dict(status=200, instance='test1'))
        self.failUnlessEqual(self.filter.backends.keys(), ['test1'])

        self.filter.process(dict(status=200, instance='test2'))
        self.failUnlessEqual(self.filter.backends.keys(), ['test1', 'test2'])

    def test_statusalarm_backends(self):
        self.filter.process(dict(status=200, instance='test1'))
        self.filter.process(dict(status=200, instance='test2'))
        self.filter.process(dict(status=503, instance='<NOSRV>'))
        self.failUnlessEqual(self.filter.watchlist, set(['test1', 'test2']))

        # The urls following a <NOSRV> should be recorded
        self.filter.process(dict(instance='test1', url='/url1'))
        self.filter.process(dict(instance='test2', url='/url2'))

        self.failUnlessEqual(self.filter.stats(), {'/url1':1, '/url2':1})

    def test_statusalarm_timeout(self):
        self.filter.process(dict(status=200, instance='test1'))
        self.filter.process(dict(status=200, instance='test2'))
        self.filter.process(dict(status=503, instance='<NOSRV>'))
        self.filter.timeout = time()-1

        # Because of the timeout, urls are not recorded
        self.filter.process(dict(instance='test2', url='/url1'))

        self.failIf(self.filter.watchlist)
        self.failIf(self.filter.timeout)

        self.failIf(self.filter.stats(), {'/url1':1, '/url2':1})
