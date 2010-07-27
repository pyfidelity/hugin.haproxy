from hugin.haproxy.goals import GoalAnalyser
from hugin.haproxy.configuration import FilterConfig
from argparse import ArgumentParser
from fileinput import input, hook_compressed
from csv import writer
from os.path import join


def main():
    parser = ArgumentParser(description='Analyse haproxy logs.')
    parser.add_argument('-d', '--directory', help='output directory', default='.')
    parser.add_argument('config', help='name of the configuration file')
    parser.add_argument('log', nargs='*', help='haproxy log files')
    args = parser.parse_args()

    config = FilterConfig()
    config.read(args.config)
    urls = config.urls()

    analyser = GoalAnalyser(input(args.log, openhook=hook_compressed),
        location=args.directory, urls=urls)
    analyser()

    csvname = join(args.directory, 'index.csv')
    generateStatsIndex(open(csvname, 'wb'), config)


def generateStatsIndex(output, config):
    csv = writer(output)
    csv.writerow(('section', 'title', 'limit'))
    for section in config.sections():
        items = dict(config.items(section))
        csv.writerow((section, items.get('title', section),
            int(items.get('max', 3000))))
