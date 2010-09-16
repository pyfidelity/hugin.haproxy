from hugin.haproxy.goals import GoalAnalyser
from hugin.haproxy.configuration import FilterConfig
from argparse import ArgumentParser
from warnings import filterwarnings
from fileinput import input, hook_compressed
from csv import writer
from os.path import join
from pkg_resources import resource_listdir, resource_isdir, resource_string


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

    generateStatsHTML(args.directory)

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


def generateStatsHTML(directory):
    pkg = 'hugin.haproxy'
    base_path = 'stats'
    paths = ['.']
    while paths:
        path = paths.pop()
        for item in resource_listdir(pkg, join(base_path, path)):
            if item.startswith('.'):
                continue
            item_path = join(path, item)
            if resource_isdir(pkg, join(base_path, item_path)):
                paths.append(item_path)
            else:
                f = open(join(directory, item_path), 'wb')
                f.write(resource_string(pkg, join(base_path, item_path)))
                f.close()
