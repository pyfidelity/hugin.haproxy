import unittest
from hugin.haproxy.filters.timingstats import TimingAverage, TimingStatistics
from hugin.haproxy.syslog import SyslogResource


class Stats(object):
    def __init__(self, data):
        self.data = data

    def stats(self):
        return self.data


class TestSyslogResource(unittest.TestCase):

    def test_basic_zero(self):
        stats = Stats(dict(total=0.0, response=0.0, wait=0.0))
        resource = SyslogResource(stats)
        expect = """total:0.0
response:0.0
wait:0.0"""
        self.failUnlessEqual(resource.render_GET(None), expect)

    def test_basic_values(self):
        # Test the most basic numbers and reset function
        stats = Stats(dict(total=3.0, response=2.0, wait=1.1))
        resource = SyslogResource(stats)
        expect = """total:3.0
response:2.0
wait:1.1"""
        self.failUnlessEqual(resource.render_GET(None), expect)
