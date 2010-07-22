from csv import DictWriter
import datetime
import itertools
import os
import warnings

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
        self._statscounters = {}
        self._outputs = {}
        self._files = {}
        
        self.parse = logparser()
        
        self._instantiateFilters()
        self._instantiateCSVWriters()

    def _instantiateFilters(self):
        for name in self.urls:
            self._statscounters[name] = TimingStatistics() 

    def _instantiateCSVWriters(self):
        for name in self.urls:
            location = os.path.join(self.dir, '%s_stats.csv' % name)
            backing = open(location, 'w')
            self._files[name] = backing
            
            keys = ['date', ] + TimingStatistics().stats().keys()
            
            writer = DictWriter(backing, keys)
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
        self.getDateForLine(line)
        for name in self.statscounters.keys():
            condition = self.urls[name]
            if condition[1].match(line['url']) and condition[0] == line['method']:
                return name
    
    def getDateForLine(self, line):
        date = datetime.datetime.strptime(line['date'], DATE_FORMAT)
        return date.date()
    
    def __call__(self):
        iterable = itertools.imap(self.parse, self.log)
        days = itertools.groupby(iterable, self.getDateForLine)
        
        for day, iterable in days:

            parsed, destination = itertools.tee(iterable)
            destination = itertools.imap(self.filterForLine, destination)
        
            classified = itertools.izip(destination, parsed)
        
            for destination, entry in classified:
                try:
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
        
        
        
