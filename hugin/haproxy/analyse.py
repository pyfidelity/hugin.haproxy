from hugin.haproxy.goals import GoalAnalyser
from hugin.haproxy.configuration import FilterConfig
from argparse import ArgumentParser
from warnings import filterwarnings
from fileinput import input, hook_compressed
from csv import writer
from os.path import join


def main():
    parser = ArgumentParser(description='Analyse haproxy logs.')
    parser.add_argument('-q', '--quiet', help='suppress warnings', action='store_true')
    parser.add_argument('-p', '--past-only', help='do not output statistics for today', action='store_true')
    parser.add_argument('-d', '--directory', help='output directory', default='.')
    parser.add_argument('config', help='name of the configuration file')
    parser.add_argument('log', nargs='*', help='haproxy log files')
    args = parser.parse_args()

    if args.quiet:
        filterwarnings('ignore')

    config = FilterConfig()
    config.read(args.config)

    analyser = GoalAnalyser(input(args.log, openhook=hook_compressed),
        location=args.directory, config=config, past_only=args.past_only)
    analyser()

    csvname = join(args.directory, 'index.csv')
    generateStatsIndex(open(csvname, 'wb'), config)


def generateStatsIndex(output, config):
    csv = writer(output)
    csv.writerow(('section', 'title', 'limit', 'description'))
    for section in config.sections():
        items = dict(config.items(section))
        csv.writerow((
            section,
            items.get('title', section),
            int(items.get('max', 3000)),
            items.get('description', ''),
            ))
