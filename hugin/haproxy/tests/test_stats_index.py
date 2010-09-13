from unittest import TestCase
from io import BytesIO
from hugin.haproxy.analyse import generateStatsIndex
from hugin.haproxy.configuration import FilterConfig


config = """
[home]
method = GET
match = ^/$
max = 2000
title = Home page

[about]
method = GET
match = ^/about$
"""


class TestGenerateHTML(TestCase):

    def setUp(self):
        self.config = FilterConfig()
        self.config.readfp(BytesIO(config))

    def test_index_generated_for_rule(self):
        output = BytesIO()
        generateStatsIndex(output, self.config)
        self.assertEqual(output.getvalue().splitlines(), [
            'section,title,limit,description',
            'home,Home page,2000,',
            'about,about,3000,',
        ])
