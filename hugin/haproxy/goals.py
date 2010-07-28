from csv import DictWriter, DictReader
import datetime
import itertools
import os
import warnings

from paste.util.multidict import MultiDict

from hugin.haproxy.filters.timingstats import TimingStatistics
from hugin.haproxy.logparser import logparser, DATE_FORMAT

class GoalAnalyser(object):
    """Takes a log file and some filters for URL specific stats and generates 
    CSV files with the result of the TimingStatistics filter"""
    
    def __init__(self, log, location, urls={}):
        super(GoalAnalyser, self).__init__()
        self.log = log
        self.urls = urls
        self.dir = location
        self._statscounters = MultiDict()
        self._outputs = {}
        self._files = {}
        self._existing_dates = {}
        
        self.parse = logparser()

    def _instantiateFilters(self):
        for name in self.urls:
            self._statscounters[name] = TimingStatistics() 

    def _instantiateCSVWriters(self):
        keys = ['date', ] + TimingStatistics().stats().keys()

        for name in self.urls:
            location = os.path.join(self.dir, '%s_stats.csv' % name)

            if os.path.exists(location):
                # We are going to add to an existing file.
                backing = open(location, 'r+')
                reader = DictReader(backing)
                self._existing_dates[name] = [r['date'] for r in reader]
            else:
                backing = open(location, 'w')
            
            self._files[name] = backing
                    
            writer = DictWriter(backing, keys)
            if self._existing_dates.get(name, None) is None:
                writer.writerow(dict(zip(keys, keys)))
            
            self._outputs[name] = writer

    @property
    def filters(self):
        return self.urls.keys()

    @property
    def statscounters(self):
        return self._statscounters
    
    @property
    def outputs(self):
        return self._outputs
    
    def filterForLine(self, line):
        """Take a parsed log line and return the rule name that it matches 
        or None if none match."""
        
        self.getDateForLine(line)
        for name in self.statscounters.keys():
            condition = self.urls[name]
            if condition[1].match(line['url']) and condition[0] == line['method']:
                return name
    
    def getDateForLine(self, line):
        """Return a python datetime accurate to the date level for the day 
        this line took place on."""
        date = datetime.datetime.strptime(line['date'], DATE_FORMAT)
        return date.date()
    
    def __call__(self):
        
        self._instantiateFilters()
        self._instantiateCSVWriters()
        
        # We know the dates are in order, so parse them and groupby their date
        iterable = itertools.imap(self.parse, self.log)
        iterable = itertools.ifilter(lambda x: x is not None, iterable)
        
        days = itertools.groupby(iterable, self.getDateForLine)
        
        for day, iterable in days:
            # Duplicate the iterator for each day, find the responsible rule 
            # name and turn it into a dictionary.iteritems() style iterator.
            parsed, destination = itertools.tee(iterable)
            destination = itertools.imap(self.filterForLine, destination)
            classified = itertools.izip(destination, parsed)
        
            for destination, entry in classified:
                try:
                    # Pass the line onto the underlying stats class
                    if day.isoformat() in self._existing_dates.get(destination, []):
                        continue
                    self.statscounters[destination].process(entry)
                except KeyError:
                    warnings.warn("%s for %s is not classified" % (entry['method'], entry['url']))
                    continue
        
            for name in self.filters:
                stats = self.statscounters[name].stats()
                if not any(stats.values()):
                    # We have no data at all, skip this
                    warnings.warn("No data for %s on %s" % (name, day.isoformat()))
                    continue
                stats['date'] = day.isoformat()
                self.outputs[name].writerow(stats)
            
        self.finish()
    
    def finish(self):
        for f in self._files.values():
            f.flush()
            os.fsync(f.fileno())
            f.close()
