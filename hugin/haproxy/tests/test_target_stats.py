from csv import DictReader
import re
import unittest
import tempfile
from io import BytesIO
import os
import shutil

from paste.util.multidict import MultiDict

from hugin.haproxy.goals import GoalAnalyser

SAMPLE_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" """

BOGUS_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/wibble/wobble/woo HTTP/1.0" """

INVALID_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 


wibble wobble wooYAY!
"""

NEWS_AND_GENERAL_LOG = """Jul 21 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/sdf HTTP/1.0" 
Jul 21 17:26:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:26:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/news/sdfs HTTP/1.0" 
Jul 21 17:27:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:27:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/news/fd HTTP/1.0" 
Jul 21 17:28:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [21/Jul/2010:17:28:59.434] zopecluster zope/backend 0/0/0/395/396 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/gsdew HTTP/1.0" """


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

MULTI_WEEK_LOG = """Jul 01 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [01/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 02 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [02/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 03 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [03/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 04 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [04/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 05 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [05/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 06 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [06/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 07 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [07/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 08 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [08/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 09 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [09/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 10 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [10/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 11 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [11/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 12 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [12/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/900 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 13 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [13/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/100 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 14 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [14/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/100 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 15 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [15/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/100 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0"
Jul 16 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [16/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/100 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 17 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [17/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/100 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 18 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [18/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/100 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" 
Jul 19 17:25:59 127.0.0.1 haproxy[2474]: 127.0.0.1:49275 [19/Jul/2010:17:25:59.434] zopecluster zope/backend 0/0/0/0/100 200 3535 - - ---- 0/0/0/0/0 0/0 "GET /VirtualHostBase/http/www.site.example:80/subsite/VirtualHostRoot/ HTTP/1.0" """


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
        self.analyser()
        
        self.assertEqual(len(self.analyser.statscounters), 1)
        self.assertEqual(self.analyser.statscounters.keys(), ["home"])

    def test_sample_filtered_to_home(self):
        self.analyser()
        
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
2009-01-02,396,396,151.0,94,396,245,396
""")
        prep.close()
        del prep
        
        self.analyser()
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 4) # Header row, two historical, one new

    def test_multiple_runs_dont_cause_dupes(self):
        self.analyser()
        del self.analyser
        
        self.analyser = GoalAnalyser(BytesIO(SAMPLE_LOG), location=self.location, urls={ 'home':('GET', re.compile("^/?$")), })
        self.analyser()
        
        location = os.path.join(self.location, 'home_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # Header row, one new

    
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
        self.analyser()
        
        self.assertEqual(len(self.analyser.statscounters), 3)
        self.assertEqual(self.analyser.statscounters.keys(), ["home", "register", "news"])

    def test_sample_filtered_to_home(self):
        self.analyser()
        
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


class TestOrderingOfRulesSetsPrecedent(TempdirAvailable):
    """These tests need to use a multidict to preserve ordering.  See 
    test_config for proof that's what our config parser gives us."""
    
    def setUp(self):
        TempdirAvailable.setUp(self)

    def test_catch_all_last(self):
        """If the all rule is processed second some things will go into news"""
        configs = MultiDict()
        configs['news'] = ('GET', re.compile("^/news"))
        configs['all'] = ('GET', re.compile("^/(.*)$"))
        
        self.analyser = GoalAnalyser(BytesIO(NEWS_AND_GENERAL_LOG), location=self.location, urls=configs)

        self.analyser()
        location = os.path.join(self.location, 'all_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # Header row and one day
        
        location = os.path.join(self.location, 'news_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # Header row and one day

    def test_catch_all_first(self):
        """If the all rule is processed first it will use all the data and 
        other stats files will be empty."""
        configs = MultiDict()
        configs['all'] = ('GET', re.compile("^/(.*)$"))
        configs['news'] = ('GET', re.compile("^/news"))
        
        self.analyser = GoalAnalyser(BytesIO(NEWS_AND_GENERAL_LOG), location=self.location, urls=configs)

        self.analyser()
        location = os.path.join(self.location, 'all_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 2) # Header row and one day
        
        location = os.path.join(self.location, 'news_stats.csv')
        output = open(location, 'r').readlines()
        self.assertEqual(len(output), 1) # Header row only - no stats



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

class TestHistogram(TempdirAvailable):
    
    def setUp(self):
        TempdirAvailable.setUp(self)
        configs = { 'all':('GET', re.compile("^/(.*)$")), }
        self.analyser = GoalAnalyser(BytesIO(MULTI_WEEK_LOG), location=self.location, urls=configs)

    def read_csv(self, name):
        location = os.path.join(self.location, name)
        return list(DictReader(open(location, 'r')))

    def test_stats_have_rolling_averages(self):
        self.analyser()
        values = self.read_csv('all_stats.csv')
        self.assertEqual(len(values), 19) # the log covers 19 days
        self.failUnless("date" in values[0])
        self.failUnless("1d80" in values[0])
        self.failUnless("7d80" in values[0])
        self.failUnless("1avg" in values[0])
        self.failUnless("7avg" in values[0])
    
    def test_last_rolling_average_only_contains_last_seven_days(self):
        self.analyser()
        values = self.read_csv('all_stats.csv')
        self.assertEqual(values[-1]['7avg'], '100')
        self.assertEqual(values[-1]['7stddev'], '0.0')
        
    def test_percentiles_drop_after_performance_improvement(self):
        self.analyser()
        values = self.read_csv('all_stats.csv')
        # 90% drops at last day
        self.assertEqual(values[-1]['7d90'], '100')
        self.assertEqual(values[-2]['7d90'], '900')
        # 80% drops one day earlier
        self.assertEqual(values[-1]['7d80'], '100')
        self.assertEqual(values[-2]['7d80'], '100')
        self.assertEqual(values[-3]['7d80'], '900')
