import unittest
from hugin.haproxy.filters.fourohfour import FourOhFour
from hugin.haproxy.syslog import SyslogResource

class TestFourOhFour(unittest.TestCase):

    def setUp(self):
        self.filter = FourOhFour()

    def test_404_empty(self):
        self.failUnlessEqual(self.filter.stats(), dict())

        self.filter.process(dict())
        self.failUnlessEqual(self.filter.stats(), dict())

    def test_404_basic(self):
        # Test the most basic numbers and reset function
        self.filter.process(dict(status=404,url='/securityhole.asp'))
        self.failUnlessEqual(self.filter.stats(reset=False), {'/securityhole.asp':1})
        self.failUnlessEqual(self.filter.stats(), {'/securityhole.asp':1})

    def test_404_statsfilter(self):
        # Test the most basic numbers and reset function
        for i in range(30):
            self.filter.process(dict(status=404,url='/securityhole.asp'))
        for i in range(25):
            for j in range(i):
                self.filter.process(dict(status=404,url='/%d.asp'%i))
        expect = {'/securityhole.asp':30, '/24.asp':24}
        self.failUnlessEqual(self.filter.stats(reset=False, count=2), expect)
        self.failUnlessEqual(self.filter.stats(count=2), expect)
        self.failUnlessEqual(self.filter.stats(), {})
