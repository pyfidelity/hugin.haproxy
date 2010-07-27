import unittest
from io import BytesIO
from hugin.haproxy.analyse import generateHTML
from hugin.haproxy.configuration import FilterConfig

class TestGenerateHTML(unittest.TestCase):

    def setUp(self):
        
        config = BytesIO("""
[home]
method = GET
match = ^/$
max = 3000
title = Home page
""")
        
        self.config = FilterConfig()
        self.config.readfp(config)
        
    def test_graph_generated_for_rule(self):
        html = generateHTML(self.config)
        self.failUnless('''<div id="home" class="chart 3000"></div>''' in html)
        self.failUnless('''<h3>Home page</h3>''' in html)
