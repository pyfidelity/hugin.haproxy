import re
import unittest
import tempfile
from io import BytesIO
import os

from hugin.haproxy.goals import GoalAnalyser

SAMPLE_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" """

LONGER_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 22 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [22/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 23 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [23/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 24 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [24/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" """

MULTI_ENTRY_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/122/122 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/331/331 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 22 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [22/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 22 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [22/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/91/94 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 23 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [23/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 24 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [24/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/1212/1212 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" """

class TestSimpleConfiguration(unittest.TestCase):

    def setUp(self):
        configs = { 'home':('GET', re.compile("^/?$")), }
        
        self.analyser = GoalAnalyser(BytesIO(SAMPLE_LOG), location=tempfile.gettempdir(), urls=configs)

    def test_stats_counter_instantiated(self):
        self.assertEqual(len(self.analyser.statscounters), 1)
        self.assertEqual(self.analyser.statscounters.keys(), ["home"])

    def test_sample_filtered_to_home(self):
        parsed = self.analyser.parse(SAMPLE_LOG)
        self.assertEqual(self.analyser.filterForLine(parsed), 'home')
    
    def test_running_dumps_into_output(self):
        self.analyser()
        location = os.path.join(tempfile.gettempdir(), 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # Header row and one day

class TestMultipleTargetsInConfiguration(unittest.TestCase):

    def setUp(self):
        configs = { 'home':('GET', re.compile("^/?$")), 
                    'news':('GET', re.compile("^/news")), 
                    'register':('POST', re.compile("^/register$")), }
        
        self.analyser = GoalAnalyser(BytesIO(SAMPLE_LOG), location=tempfile.gettempdir(), urls=configs)

    def test_all_counters_initialised(self):
        self.assertEqual(len(self.analyser.statscounters), 3)
        self.assertEqual(self.analyser.statscounters.keys(), ["home", "register", "news"])

    def test_sample_filtered_to_home(self):
        parsed = self.analyser.parse(SAMPLE_LOG)
        self.assertEqual(self.analyser.filterForLine(parsed), 'home')
    
    def test_running_dumps_into_output(self):
        self.analyser()
        location = os.path.join(tempfile.gettempdir(), 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # Header row and one day
        
        location = os.path.join(tempfile.gettempdir(), 'register_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 1) # Header row only
         
        location = os.path.join(tempfile.gettempdir(), 'news_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 1) # Header row only


class TestSummary(unittest.TestCase):

    def setUp(self):
        self.configs = { 'home':('GET', re.compile("^/?$")), }

    def test_multiple_days_have_multiple_rows(self):
        self.analyser = GoalAnalyser(BytesIO(LONGER_LOG), location=tempfile.gettempdir(), urls=self.configs)
        
        self.analyser()
        location = os.path.join(tempfile.gettempdir(), 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 5) # Header row and one day
    
    def test_data_for_one_day_is_combined_into_aggregates(self):
        self.analyser = GoalAnalyser(BytesIO(MULTI_ENTRY_LOG), location=tempfile.gettempdir(), urls=self.configs)

        self.analyser()
        location = os.path.join(tempfile.gettempdir(), 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 5) # Header row and one day
