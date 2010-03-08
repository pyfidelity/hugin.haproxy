import unittest
from hugin.haproxy.filters.userstate import UserState

class TestUserState(unittest.TestCase):

    def setUp(self):
        self.stats = UserState()

    def test_average_empty(self):
        self.failUnlessEqual(self.stats.stats(), dict(duplicates=0,redispatch=0,affinity=0))

        self.stats.process(dict())
        self.failUnlessEqual(self.stats.stats(), dict(duplicates=0,redispatch=0,affinity=0))

    def test_affinity(self):
        self.stats.process(dict(reqcookie='__ac="user',
                                terminationevent='-',
                                url='/url1',
                                instance='instance'))
        self.failUnlessEqual(self.stats.stats(reset=False), dict(duplicates=0,redispatch=0,affinity=0))

        self.stats.process(dict(reqcookie='__ac="user',
                                terminationevent='-',
                                url='/url2',
                                instance='instance'))
        self.failUnlessEqual(self.stats.stats(reset=False), dict(duplicates=0,redispatch=0,affinity=1))

        self.stats.process(dict(reqcookie='__ac="user',
                                terminationevent='-',
                                url='/url3',
                                instance='instance'))
        self.failUnlessEqual(self.stats.stats(reset=False), dict(duplicates=0,redispatch=0,affinity=2))

    def test_redispatch(self):
        for i in range(4):
            self.stats.process(dict(reqcookie='__ac="user',
                                    terminationevent='-',
                                    url='/url',
                                    instance='instance'))

        self.failUnlessEqual(self.stats.stats(reset=False), dict(duplicates=0,redispatch=0,affinity=3))

        self.stats.process(dict(reqcookie='__ac="user',
                                terminationevent='-',
                                url='/url',
                                instance='different'))
        self.failUnlessEqual(self.stats.stats(reset=False), dict(duplicates=0,redispatch=1,affinity=3))

        # When going back to instance we don't have affinity, but we don't have redispatch either
        # because we consider it affinity after 4 requests to same instance
        self.stats.process(dict(reqcookie='__ac="user',
                                terminationevent='-',
                                url='/url',
                                instance='instance'))
        self.failUnlessEqual(self.stats.stats(reset=False), dict(duplicates=0,redispatch=1,affinity=3))

    def test_duplicates(self):
        self.stats.process(dict(reqcookie='__ac="user',
                                terminationevent='C',
                                url='/url',
                                instance='instance'))
        self.stats.process(dict(reqcookie='__ac="user',
                                terminationevent='-',
                                url='/url',
                                instance='instance'))
        self.failUnlessEqual(self.stats.stats(), dict(duplicates=1,redispatch=0,affinity=1))
