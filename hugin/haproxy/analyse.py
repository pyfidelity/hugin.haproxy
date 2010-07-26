from hugin.haproxy.goals import GoalAnalyser
from hugin.haproxy.configuration import FilterConfig
from argparse import ArgumentParser
from fileinput import input
from re import compile


def main():
    parser = ArgumentParser(description='Analyse haproxy logs.')
    parser.add_argument('-d', '--directory', help='output directory', default='.')
    parser.add_argument('config', help='name of the configuration file')
    parser.add_argument('log', nargs='*', help='haproxy log files')
    args = parser.parse_args()

    config = FilterConfig()
    config.read(args.config)
    urls = config.urls()

    analyser = GoalAnalyser(input(args.log), location=args.directory, urls=urls)
    analyser()
