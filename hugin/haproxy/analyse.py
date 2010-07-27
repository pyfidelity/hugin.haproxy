from hugin.haproxy.goals import GoalAnalyser
from hugin.haproxy.configuration import FilterConfig
from argparse import ArgumentParser
from fileinput import input, hook_compressed
from re import compile
import os

def main():
    parser = ArgumentParser(description='Analyse haproxy logs.')
    parser.add_argument('-d', '--directory', help='output directory', default='.')
    parser.add_argument('config', help='name of the configuration file')
    parser.add_argument('log', nargs='*', help='haproxy log files')
    args = parser.parse_args()

    config = FilterConfig()
    config.read(args.config)
    urls = config.urls()

    analyser = GoalAnalyser(input(args.log, openhook=hook_compressed), location=args.directory, urls=urls)
    analyser()
    
    with open(os.path.join(args.directory, "index.html"), "w") as html_out:
        html_out.write(generateHTML(config))

SECTION = """<h3>%(title)s</h3><div id="%(id)s" class="chart maxval-%(max)d"></div><br />"""

def generateHTML(config):
    location = os.path.join(os.path.dirname(__file__), "stats_template.html")
    with open(location, "r") as f:
        template = f.read()
        
    charts = ''

    for section, items in config._sections.items():
        vals = {"id":section, "title":items.get('title', section), "max":int(items.get('max', "3000"))}
        charts += SECTION % vals
    
    return template % (charts)