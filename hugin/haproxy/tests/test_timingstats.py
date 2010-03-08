import unittest
from hugin.haproxy.filters.timingstats import TimingAverage, TimingStatistics

class TestAverage(unittest.TestCase):

    def setUp(self):
        self.stats = TimingAverage()

    def test_average_empty(self):
        self.failUnlessEqual(self.stats.stats(), dict(wait=0,response=0,total=0))

        self.stats.process(dict())
        self.failUnlessEqual(self.stats.length, 1)
        self.failUnlessEqual(self.stats.stats(), dict(wait=0,response=0,total=0))

    def test_average_basic(self):
        # Test the most basic numbers and reset function
        self.stats.process(dict(Tw=1,Tr=2,Tt=3))
        self.failUnlessEqual(self.stats.stats(reset=False), dict(wait=1,response=2,total=3))
        self.failUnlessEqual(self.stats.stats(), dict(wait=1,response=2,total=3))

    def test_average(self):
        self.stats.process(dict(Tw=1,Tr=2,Tt=3))
        self.stats.process(dict(Tw=9,Tr=8,Tt=7))
        self.failUnlessEqual(self.stats.stats(), dict(wait=5,response=5,total=5))


class TestStatistics(unittest.TestCase):

    def setUp(self):
        self.stats = TimingStatistics()

    def test_basic_empty(self):
        self.failUnlessEqual(self.stats.stats(), dict(ten=0,median=0,ninety=0,avg=0,max=0))

        self.stats.process(dict())
        expect = dict(ten=0,median=0,ninety=0,avg=0,max=0)
        res = self.stats.stats()
        self.failUnlessEqual(res, expect, 
                             ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))

    def test_basic_reset(self):
        # Test the most basic numbers and reset function
        self.stats.process(dict(Tt=3))
        expect = dict(ten=3,median=3,ninety=3,avg=3,max=3)
        res = self.stats.stats(reset=False)
        self.failUnlessEqual(res, expect, 
                             ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))

        res = self.stats.stats()
        self.failUnlessEqual(res, expect, 
                             ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))

    def test_statistics(self):
        for i in range(1,12):
            self.stats.process(dict(Tt=i))
        expect = dict(ten=2,median=6,ninety=10,avg=6,max=11)
        res = self.stats.stats()
        self.failUnlessEqual(res, expect, 
                             ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))
