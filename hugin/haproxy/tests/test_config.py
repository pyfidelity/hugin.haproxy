from io import BytesIO
import re
import unittest

from hugin.haproxy.configuration import FilterConfig

REGEX_TYPE = type(re.compile("^"))

class TestSimpleConfiguration(unittest.TestCase):

    def setUp(self):
        self.parser = FilterConfig()
        
    def test_one_rule_one_section(self):
        config = BytesIO("""
[home]
method = GET
match = ^/$
""")
        self.parser.readfp(config)
        self.assertEqual(self.parser.sections(), ['home'])
        self.assertEqual(len(self.parser._sections), 1)
                
    def test_duplicate_rules_one_section(self):
        # We've decided we don't care about this for now. If we ever need
        # to gather stats on things that need multiple HTTP methods reinstate
        # this, otherwise just use regex's (foo|bar) syntax.
        return NotImplemented
        
        config = BytesIO("""
[home]
method = GET
match = ^/$

[home]
method = GET
match = ^/home$

""")
        self.parser.readfp(config)
        self.assertEqual(self.parser.sections(), ['home'])
        self.assertEqual(len(self.parser._sections), 2)
        
    def test_match_objects_are_regexes(self):
        config = BytesIO("""
[home]
method = GET
match = ^/$
""")
        self.parser.readfp(config)
        match = self.parser.get('home', 'match')
        regex = re.compile("^")
        self.assertEqual(type(match), REGEX_TYPE)
    
    def test_urls_method_returns_dict_of_tuples(self):
        config = BytesIO("""
[home]
method = GET
match = ^/$
""")
        self.parser.readfp(config)
        urls = self.parser.urls()
                
        self.assertEqual(urls.keys(), ['home'])
        self.assertEqual(urls['home'][0], "GET")
        self.assertEqual(type(urls['home'][1]), REGEX_TYPE)
        