from csv import DictWriter, DictReader
from collections import deque, defaultdict
import numpy
import datetime
import itertools
import os
import warnings

from paste.util.multidict import MultiDict

from hugin.haproxy.logparser import logparser, DATE_FORMAT


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

    def process(self, data):
        date = getDateForLine(data)
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

    def __init__(self, log, location, urls={}, avgs=[1, 7], past_only=False):
        super(GoalAnalyser, self).__init__()
        self.log = log
        self.urls = urls
        self.avgs = avgs
        self.dir = location
        self.past_only = past_only
        self.statscounters = MultiDict()
        self.outputs = {}
        self.files = {}
        self.existing_dates = {}
        self.parse = logparser()

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
        for name in self.statscounters.keys():
            method, url_pattern = self.urls[name]
            url = line['url']
            qs = line['querystring']
            if qs is not None:
                url += qs
            if url_pattern.match(url) and method == line['method']:
                return name

    def __call__(self):
        self._instantiateFilters()
        self._instantiateCSVWriters()
        # We know the dates are in order, so parse them and groupby their date
        iterable = itertools.imap(self.parse, self.log)
        iterable = itertools.ifilter(lambda x: x is not None, iterable)
        days = itertools.groupby(iterable, getDateForLine)
        existing = self.existing_dates
        for day, iterable in days:
            if self.past_only and day == datetime.date.today():
                continue
            # Duplicate the iterator for each day, find the responsible rule
            # name and turn it into a dictionary.iteritems() style iterator.
            parsed, destination = itertools.tee(iterable)
            destination = itertools.imap(self.filterForLine, destination)
            classified = itertools.izip(destination, parsed)
            for destination, entry in classified:
                try:
                    # Pass the line onto the underlying stats class
                    if day.isoformat() in existing.get(destination, []):
                        continue
                    self.statscounters[destination].process(entry)
                except KeyError:
                    warnings.warn("%s for %s is not classified" %
                        (entry['method'], entry['url']))
                    continue
            for name in self.urls:
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
