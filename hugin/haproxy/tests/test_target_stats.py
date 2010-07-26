from csv import DictReader
import re
import unittest
import tempfile
from io import BytesIO
import os
import shutil

from hugin.haproxy.goals import GoalAnalyser

SAMPLE_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" """

BOGUS_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/wibble/wobble/woo HTTP/1.0" """

INVALID_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 


wibble wobble wooYAY!
"""


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


class TempdirAvailable(unittest.TestCase):
    
    def setUp(self):
        self.location = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.location)


class TestSimpleConfiguration(TempdirAvailable):

    def setUp(self):
        TempdirAvailable.setUp(self)
        configs = { 'home':('GET', re.compile("^/?$")), }
        
        self.analyser = GoalAnalyser(BytesIO(SAMPLE_LOG), location=self.location, urls=configs)

    def test_stats_counter_instantiated(self):
        self.assertEqual(len(self.analyser.statscounters), 1)
        self.assertEqual(self.analyser.statscounters.keys(), ["home"])

    def test_sample_filtered_to_home(self):
        parsed = self.analyser.parse(SAMPLE_LOG)
        self.assertEqual(self.analyser.filterForLine(parsed), 'home')
    
    def test_running_dumps_into_output(self):
        self.analyser()
        location = os.path.join(self.location, 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # Header row and one day
    
    def test_historical_data_is_left_intact(self):
        location = os.path.join(self.location, 'home_stats.csv')
        prep = open(location, 'w')
        prep.write("""date,median,ninety,stddev,ten,max,avg,eighty
2009-01-01,331,396,116.895965143,122,396,283,396
2009-01-02,396,396,151.0,94,396,245,396""")
        
        self.analyser()
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 4) # Header row, two historical, one new
    
    def test_csv_is_in_a_valid_format(self):
        self.analyser()

        location = os.path.join(self.location, 'home_stats.csv')
        prep = open(location, 'r')
        csv = DictReader(prep)
        self.failUnless(len(list(csv)), 1)

    

class TestInvalidLogEntry(TempdirAvailable):
    
    def setUp(self):
        TempdirAvailable.setUp(self)

        configs = { 'home':('GET', re.compile("^/?$")), }
        
        self.analyser = GoalAnalyser(BytesIO(INVALID_LOG), location=self.location, urls=configs)
    
    def test_empty_output_without_errors(self):
        self.analyser()
        location = os.path.join(self.location, 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # There is a single valid line at the start of the input

class TestUnknownLogEntry(TempdirAvailable):
    
    def setUp(self):
        TempdirAvailable.setUp(self)

        configs = { 'home':('GET', re.compile("^/?$")), }
        
        self.analyser = GoalAnalyser(BytesIO(BOGUS_LOG), location=self.location, urls=configs)
    
    def test_empty_output_without_errors(self):
        self.analyser()
        location = os.path.join(self.location, 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 1)

class TestMultipleTargetsInConfiguration(TempdirAvailable):

    def setUp(self):
        TempdirAvailable.setUp(self)

        configs = { 'home':('GET', re.compile("^/?$")), 
                    'news':('GET', re.compile("^/news")), 
                    'register':('POST', re.compile("^/register$")), }
        
        self.analyser = GoalAnalyser(BytesIO(SAMPLE_LOG), location=self.location, urls=configs)

    def test_all_counters_initialised(self):
        self.assertEqual(len(self.analyser.statscounters), 3)
        self.assertEqual(self.analyser.statscounters.keys(), ["home", "register", "news"])

    def test_sample_filtered_to_home(self):
        parsed = self.analyser.parse(SAMPLE_LOG)
        self.assertEqual(self.analyser.filterForLine(parsed), 'home')
    
    def test_running_dumps_into_output(self):
        self.analyser()
        location = os.path.join(self.location, 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # Header row and one day
        
        location = os.path.join(self.location, 'register_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 1) # Header row only
         
        location = os.path.join(self.location, 'news_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 1) # Header row only

class TestSummary(TempdirAvailable):

    def setUp(self):
        TempdirAvailable.setUp(self)

        self.configs = { 'home':('GET', re.compile("^/?$")), }

    def test_multiple_days_have_multiple_rows(self):
        self.analyser = GoalAnalyser(BytesIO(LONGER_LOG), location=self.location, urls=self.configs)
        
        self.analyser()
        location = os.path.join(self.location, 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 5) # Header row and one day
    
    def test_data_for_one_day_is_combined_into_aggregates(self):
        self.analyser = GoalAnalyser(BytesIO(MULTI_ENTRY_LOG), location=self.location, urls=self.configs)

        self.analyser()
        location = os.path.join(self.location, 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 5) # Header row and one day
