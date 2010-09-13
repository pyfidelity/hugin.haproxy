import re
from csv import DictWriter, DictReader
from collections import deque, defaultdict
import numpy
import datetime
import itertools
import os
import warnings

from paste.util.multidict import MultiDict

from hugin.haproxy.logparser import logparser, DATE_FORMAT


LOG_FORMAT = '{ip} - - [{date} +0000] "{method} {url}{querystring} HTTP/1.0" {status} {bytes} {frontend} {backend}\n'

def getDateForLine(line):
    """Return a python datetime accurate to the date level for the day
    this line took place on."""
    date = datetime.datetime.strptime(line['date'], DATE_FORMAT)
    date += datetime.timedelta(milliseconds=line['Tt'])
    return date.date()


def valueForPercentile(stats, percentile):
    if not stats:
        return 0
    length = len(stats)
    return stats[min(int(length*percentile/100), length-1)]


class DailyStatistics(object):

    def __init__(self, avgs):
        self.avgs = avgs
        self.days = deque(maxlen=max(avgs))
        self.last_day = None

    def process(self, data, date):
        if not date.day == self.last_day:
            self.data = []
            self.days.append(self.data)
            self.last_day = date.day
        self.data.append(int(data.get("Tt")))

    def stats_for_days(self, days):
        data = list(self.days)[-days:]  # data for n days
        data = sorted(sum(data, []))    # concatenate & sort
        values = {}
        length = len(data)
        values['%ddlength' % days] = length
        values['%ddavg' % days] = sum(data) / length if length else 0
        values['%ddstddev' % days] = numpy.std(numpy.array(data))
        for p in range(10, 101, 10):
            values['%dd%d' % (days, p)] = valueForPercentile(data, p)
        return values

    def stats(self):
        values = defaultdict(int)
        for avg in self.avgs:
            values.update(self.stats_for_days(avg))
        return values


class GoalAnalyser(object):
    """Takes a log file and some filters for URL specific stats and generates
    CSV files with the result of the DailyStatistics filter"""

    def __init__(self, log, location, urls=None, avgs=[1, 7], past_only=False,
                 config=None):
        super(GoalAnalyser, self).__init__()
        self.config = config
        self.log = log
        if urls is None:
            if self.config is None:
                self.urls = {}
            else:
                self.urls = config.urls()
        else:
            self.urls = urls
        self.avgs = avgs
        self.dir = location
        self.past_only = past_only
        self.statscounters = MultiDict()
        self.outputs = {}
        self.files = {}
        self.existing_dates = {}
        self.parse = logparser()
        self.log_entries = {}
        if self.config is not None:
            for section in self.config.sections():
                log = dict(self.config.items(section)).get('log', '').lower()
                if log in ('true', 'yes', 'on'):
                    fn = '%s.log' % section
                    self.log_entries[section] = fn
                    self.files[fn] = open(os.path.join(self.dir, fn), 'w')

    def _instantiateFilters(self):
        for name in self.urls:
            self.statscounters[name] = DailyStatistics(self.avgs)

    def _instantiateCSVWriters(self):
        keys = ['date', ] + sorted(DailyStatistics(self.avgs).stats().keys())
        for name in self.urls:
            location = os.path.join(self.dir, '%s_stats.csv' % name)
            if os.path.exists(location):
                # We are going to add to an existing file.
                backing = open(location, 'r+')
                reader = DictReader(backing)
                self.existing_dates[name] = [r['date'] for r in reader]
            else:
                backing = open(location, 'w')
            self.files[name] = backing
            writer = DictWriter(backing, keys)
            if self.existing_dates.get(name, None) is None:
                writer.writerow(dict(zip(keys, keys)))
            self.outputs[name] = writer

    def filterForLine(self, line):
        """Take a parsed log line and return the rule name that it matches
        or None if none match."""
        status = int(line.get('status', '200'))
        if status >= 400 and status < 600:
            return
        method = line['method']
        url = line['url']
        qs = line['querystring']
        if qs is not None:
            url += qs
        for name in self.statscounters.keys():
            method_name, url_pattern = self.urls[name]
            if method_name != method:
                continue
            if url_pattern.match(url):
                return name

    def __call__(self):
        self._instantiateFilters()
        self._instantiateCSVWriters()
        # We know the dates are in order, so parse them and groupby their date
        iterable = itertools.imap(self.parse, self.log)
        iterable = itertools.ifilter(lambda x: x is not None, iterable)
        days = itertools.groupby(iterable, getDateForLine)
        existing = self.existing_dates
        # if avgs goes back several days we have to gather statistics 
        # for days in existing
        today = datetime.date.today()
        statsdays = set([str(today-datetime.timedelta(days=x)) for x in range(int(self.past_only),max(self.avgs)+int(self.past_only))])
        for day, iterable in days:
            if self.past_only and day == today:
                continue
            # Duplicate the iterator for each day, find the responsible rule
            # name and turn it into a dictionary.iteritems() style iterator.
            parsed, destination = itertools.tee(iterable)
            destination = itertools.imap(self.filterForLine, destination)
            classified = itertools.izip(destination, parsed)
            for destination, entry in classified:
                try:
                    # Pass the line onto the underlying stats class
                    if  day.isoformat() not in statsdays and day.isoformat() in existing.get(destination, []):
                        continue
                    self.statscounters[destination].process(entry, day)
                    fn = self.log_entries.get(destination)
                    if fn is not None:
                        self.files[fn].write(LOG_FORMAT.format(**entry))
                except KeyError:
                    warnings.warn("%s for %s is not classified" %
                        (entry['method'], entry['url']))
                    continue
            for name in self.urls:
                # Don't duplicate dates in csv file
                if day.isoformat() in set(sum(existing.values(), [])):
                    continue
                stats = self.statscounters[name].stats()
                if not any(stats.values()):
                    # We have no data at all, skip this
                    warnings.warn("No data for %s on %s" %
                        (name, day.isoformat()))
                    continue
                stats['date'] = day.isoformat()
                self.outputs[name].writerow(stats)
        self.finish()

    def finish(self):
        for f in self.files.values():
            f.flush()
            os.fsync(f.fileno())
            f.close()
