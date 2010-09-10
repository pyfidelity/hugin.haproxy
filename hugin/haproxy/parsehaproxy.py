# THIS IS THE OLD SCRIPT, IT IS NOT USED ANYMORE
import code
import re
import sys
import logging
from optparse import OptionParser
import signal
import threading
import time
from math import log10, pow

USAGE = """\
usage: %%prog [options]

parse parses HAProxy logs
"""

class logparser(object):
    def __init__(self):
        pattsyslogd = '(?:\w{3}\s+\d+ [\d:]{8} \S+ \S+ )?'
        pattinfo = '(?P<ip>\S+) \[(?P<date>\S+)\] (?P<frontend>\S+) (?P<backend>[\w]+)/(?P<instance>\S+) '
        patttiming = '(?P<Tq>[-\d]+)/(?P<Tw>[-\d]+)/(?P<Tc>[-\d]+)/(?P<Tr>[-\d]+)/(?P<Tt>[-\d]+) '
        patthttp = '(?P<status>\d+) (?P<bytes>\d+). (?P<reqcookie>\S+) (?P<respcookie>\S+) '
        pattterm = '(?P<terminationevent>\S)(?P<sessionstate>\S)(?P<pc>\S)(?P<opc>\S) '
        pattconn = '(?P<actconn>\d+)/(?P<feconn>\d+)/(?P<beconn>\d+)/(?P<srv_conn>\d+)/(?P<retries>[-\+\d]+) '
        pattqueue = '(?P<srv_queue>\d+)/(?P<listener_queue>\d+) '
        pattcaptures = '({(?P<captures>[^}]*)\} )?'
        patturl = '"(?P<method>\S+) (?:.*VirtualHostRoot)?(?P<url>\S*/(?P<template>[^/][^\?]+)?)?(?:\?\S*)? \S+'

        self.pattern = pattsyslogd + pattinfo + patttiming + patthttp + pattterm + pattconn + pattqueue + pattcaptures + patturl + '.*'
        self.regex = re.compile(self.pattern)

        self.blacklist = set(('/haproxy-status',))


    def list_variables(self):
        return re.findall('P<([^>]+)>', self.pattern)

    def match(self, line):
        return self.regex.match(line)


class history(object):
    """History object stores a predefined number of history entries"""
    def __init__(self, length):
        self.pos  = 0
        self.data = dict()
        self.length = length

    def add(self, data):
        self.data[self.pos] = data
        self.pos = (self.pos + 1) % self.length

    def last(self):
        return self.data.get(((self.pos - 1) % self.length),None)

    def __iter__(self):
        for i in xrange(len(self.data)):
            yield self.data[(self.pos-1-i) % self.length]
        raise StopIteration

# In monitor mode, keep track of
# Irregular status codes - 404, 503
# Irregular termination state (http://haproxy.1wt.eu/download/1.3/doc/haproxy-en.txt 4.2.4)
# Per user:
#  Session affinity/redispatch
#  Reload of pages (url+user same for consequtive requests)
# Requests per second the last ~10 seconds
TERMINATIONEVENTS = {'C':'cli abort',
                     'S':'srv abort',
                     'P':'pxy abort',
                     'R':'pxy exhau', # Proxy resource exhaustion
                     'I':'proxy err', # Internal proxy error
                     'c':'t out cli',
                     's':'t out srv',
                     '-':'         '} # Normal session completion

SESSIONSTATES = {'R':'wait clirq',
                 'Q':'wait queue',
                 'C':'wait conn ' ,
                 'H':'hdr proc  ',
                 'D':'data phase',
                 'L':'trans last',
                 'T':'tarpitted ',
                 '-':'          '} # Normal session completion

HTTPCODES = {'200':'OK',
             '201':'Created',
             '202':'Accepted',
             '204':'No content',
             '301':'Moved permanently',
             '302':'Found (Moved temporarily)',
             '304':'Not Modified',
             '401':'Unauthorized',
             '403':'Forbidden',
             '404':'Not found',
             '500':'Internal Server Error',
             '501':'Not Implemented',
             '502':'Bad Gateway',
             '503':'Service Unavailable',
             }

COOKIEMATCH = re.compile('.*="?(?P<cookie>\S+)')

class TimingCounter(object):
    
    def __init__(self):
        self.klasses  = {   '<2s': (0,2000),
                            '<4s': (2000, 4000),
                            '<6s': (4000, 6000),
                            '6s+': (6000, 10000000)
                        }
    
        self.timing_counters = dict.fromkeys(self.klasses.keys(), 0)
        self.requestcount = 0
        self.t_prev = 0
        self.t_check = lambda t, limits: t>=limits[0] and t<limits[1]     
        self.recent_stat = 'dsf'
           
    def count(self, data):
        
        Tt = int(data["Tt"])

        for klass, limits in self.klasses.items():
            if self.t_check(Tt,limits):
                self.timing_counters[klass]+=1
                break
    
    def update(self, leadtext=None):        
        
        t = int(time.time())
        if t-self.t_prev == 0:
            return
            
        tstats = self.timing_counters.copy()
        timingtotal = float(sum(self.timing_counters.values()))        
        tstats['reqsec'] = (timingtotal - self.requestcount)/(t-self.t_prev)
        self.requestcount = timingtotal
        timingkeys = ('<2s', '<4s', '<6s', '6s+')
        self.t_prev = t           
        
        if not leadtext: 
            tstats['lead'] = 'STAT ' + ' '*68
        else:
            tstats['lead'] = leadtext + ' '*(68-(len(leadtext)-5))

        for k in timingkeys:
            v = tstats.get(k,0)
            tstats['p%s'%k] = '%.1f' % (v and v*100/ timingtotal or v)

        self.recent_stat = "%(lead)s <2s:%(<2s) 5s (%(p<2s) 4s%%),  <4s:%(<4s) 4s (%(p<4s) 4s%%),  <6s:%(<6s) 3s (%(p<6s) 4s%%),  6s+:%(6s+) 2s (%(p6s+) 4s%%)    %(reqsec) 3d req/s" % tstats
       
    def update_and_print(self, out, timeout=10):                  
        t = int(time.time())
        if t-self.t_prev >= timeout:                
            self.update()                       
            out.append(self.recent_stat)     
                 
class PatternCounters(object):
    
    def __init__(self, patterns):                
        self.patterns = patterns
        
        self.pattern_counters = {}
        for k in self.patterns.keys():
            self.pattern_counters[k] = TimingCounter()

        self.t_prev = 0
        self.recent_stat = ''
        
    def count(self, data):        
        url = data['url']
        for pattern_id, pattern in self.patterns.items():
            if pattern.match(url):
                self.pattern_counters[pattern_id].count(data)
    
    def update(self):
        rs = []
    #    import pdb; pdb.set_trace()
        for cid, ctr in self.pattern_counters.items():
            leadtext = "CTRS "+cid
            ctr.update(leadtext)
            rs.append(ctr.recent_stat)
        
        self.recent_stat = '\n'.join(rs)
 
    
    def update_and_print(self, out, timeout=10):
        self.update()
        t = int(time.time())
        if t-self.t_prev >= timeout:
            self.update()            
            self.t_prev = t
            out.append("%s" % self.recent_stat)
    
    def __str__(self):
        return self.recent_stat
        
    
class Monitor(object):
    def __init__(self, inputfile, beginning, verbose, fields):
        self.inputfile = inputfile
        self.beginning = beginning
        self.verbose = verbose
        self.fields = fields
        self.cookies = {}
        self.parser = logparser()
        self.filters = [self.patternstats, self.timingstats, self.blacklist, self.userstate, self.statusalarm, self.timingalarm]
        self.status = {} # status code (int) -> count
        self.outputstring = '%(filter)s %(status)s Tw:%(Tw) 5s Tr: %(Tr) 5s Tt:%(Tt) 5s, %(reqcookie) 4s %(instance)s %(terminationevent)s %(sessionstate)s %(url)s'

        self.timing_counter = TimingCounter()
        self.pattern_counters = PatternCounters( {
                                                    '@@response' : re.compile('.*/@@response/.*'),
                                                    'atct_edit' : re.compile('.*/atct_edit.*')
                                                 })

    # filters get data and output, can modify data, and writes to output
    def blacklist(self, data, out):
        u = data['url']
        if u and u not in self.parser.blacklist:
            return data

    def userstate(self, data, out):
        match = COOKIEMATCH.match(data['reqcookie'])
        if match:
            uid = match.group('cookie')
            data['reqcookie'] = uid
            hist = self.status.get(uid, history(10)) # We keep track of the 10 last requests

            previous = hist.last()
            instances = []
            keyed = {}
            for d in hist:
                instance = d['instance']
                instances.append(instance)
                keyed[instance] = keyed.get(instance, 0) + 1

            # Detect redundant reloads
            if previous and previous['terminationevent'] == 'C' and previous['url'] == data['url']:
                tmpdata = data.copy()
                tmpdata['terminationevent'] = TERMINATIONEVENTS[tmpdata['terminationevent']]
                tmpdata['sessionstate'] = SESSIONSTATES[tmpdata['sessionstate']]
                tmpdata['filter'] = 'DUPL'
                out.append(self.outputstring % tmpdata)
                return

            elif len(instances) >= 5 and len(keyed)<4 and keyed.get(data['instance'], 0) <= (len(instances)/2):
                # If there are more than 5 entries, less than 4 unique in the list and 
                # the current one is not fewer than half the last instances
                tmpdata = data.copy()
                tmpdata['terminationevent'] = TERMINATIONEVENTS[tmpdata['terminationevent']]
                tmpdata['sessionstate'] = SESSIONSTATES[tmpdata['sessionstate']]
                tmpdata['filter'] = 'DISP'
                out.append(self.outputstring % tmpdata)
                return
                
            hist.add(data)
            self.status[uid] = hist
            # Update cookies
        return data

    def statusalarm(self, data, out):
        # Check for 404, 503
        httpok = set(('200','201','202','301','302','304'))
        termok = set(('-','C'))

        status = data['status']
        if status:
            self.status[status] = self.status.get(status,0) + 1

        if status not in httpok or data['terminationevent'] not in termok:
            tmpdata = data.copy()
            tmpdata['terminationevent'] = TERMINATIONEVENTS[tmpdata['terminationevent']]
            tmpdata['sessionstate'] = SESSIONSTATES[tmpdata['sessionstate']]
            tmpdata['filter'] = 'HTTP'
            out.append(self.outputstring % tmpdata)
        else:
            return data

    def timingalarm(self, data, out):
        # Check for 404, 503
        threshold = {'Tw':lambda x:x==-1 or x>=2000,
                     'Tr':lambda x:x==-1 or x>=4000,
                     'Tt':lambda x:x>=5000,
                     }
        if filter(None, [v(int(data[k])) for k,v in threshold.items()]):
            tmpdata = data.copy()
            tmpdata['terminationevent'] = TERMINATIONEVENTS[tmpdata['terminationevent']]
            tmpdata['sessionstate'] = SESSIONSTATES[tmpdata['sessionstate']]
            tmpdata['filter'] = 'TIME'
            out.append(self.outputstring % tmpdata)
        else:
            return data

    def timingstats(self, data, out):    
        self.timing_counter.count(data)        
        self.timing_counter.update_and_print(out, 10)
        return data

    def patternstats(self, data, out):    
        self.pattern_counters.count(data)        
        self.pattern_counters.update_and_print(out, 10)
        return data
        
    def printurl(self, data, out):
        out.append(data['url'])

    def process_line(self, line, out):
        line = line.strip()
        match = self.parser.match(line)

        if match:
            data = match.groupdict()
            for flt in self.filters:
                data = flt(data, out)
                if not data:
                    break

    def process(self):
        if self.inputfile:
            f = open(self.inputfile)
            if self.beginning:
                # Process history quietly
                for line in f:
                    out = []
                    self.process_line(line, out)
                    
                    
                    # Would be useful with verbose/quiet setting
                    if out and self.verbose:
                        print '\n'.join(out)

            else:
                f.seek(0, 2) # Go to end of file
        else:
            f = sys.stdin

        out = []
        while True:
            line = f.readline()
            if not line:
                if out:
                    print '\n'.join(out)
                out = []
                time.sleep(1)
            else:
                self.process_line(line, out)

class CSVWriter(object):
    def __init__(self, inputfile, outputfile, fields):
        self.inputfile = inputfile
        self.outputfile = outputfile
        if fields:
            self.fields = [x.strip() for x in fields.split(',')]
        else:
            self.fields = ('instance', 'Tq', 'Tw', 'Tc', 'Tr', 'Tt', 'method', 'status', 'url', 'template')

    def process(self):
        print "Processing log"
        start = time.time()
        parser = logparser()
        fields = self.fields
        blacklist = parser.blacklist

        # Input is either stdin or filename from options
        if self.inputfile:
            f = open(self.inputfile)
        else:
            f = sys.stdin

        output = open(self.outputfile, 'a')
        output.write(','.join(self.fields)+'\n')

        lineno = 0
        for line in f:
            line = line.strip()
            match = parser.match(line)

            if match:
                data = match.groupdict()
                u = data['url']
                if u and u not in blacklist:
                    output.write(','.join([str(data.get(x,'')) for x in fields])+'\n')

            lineno += 1

        output.flush()
        output.close()
        f.close()

        print 'Processed %s entries in %s seconds' % (lineno, (time.time()-start))


class Interactive(object):
    def __init__(self, inputfile):
        self.inputfile = inputfile
        self.totaltime = {} # Tt/10 as key -> set of line numbers
        self.zopetime = {} # Tr/10 as key -> set of line numbers
        self.queuetime = {} # Tw/10 as key -> set of line numbers
        self.status = {} # http status codes -> set of line numbers
        self.instance = {} # instance id -> set of line numbers
        self.url = {} # url -> set of line numbers
        self.template = {} # template -> set of line numbers

        self.urltiming = {} # url -> set of Tr

        self.log10factor = 5

    def gettime(self, inputnumber):
        return int(pow(10, 1.0*inputnumber/self.log10factor))

    def timeprocess(self, lineno, key, data, dictionary):
        v = int(data[key])
        if v>0:
            v = int(log10(v)*self.log10factor)
        else:
            v = 0
        s = dictionary.get(v, set())
        s.add(lineno)
        dictionary[v]=s

    def strprocess(self, lineno, key, data, dictionary):
        v = data[key]
        s = dictionary.get(v, set())
        s.add(lineno)
        dictionary[v]=s

    def process(self):
        print "Processing log"
        start = time.time()

        # Input is either stdin or filename from options
        if self.inputfile:
            f = open(self.inputfile)
        else:
            f = sys.stdin

        regex = logparser()

        lineno = 0
        for line in f:
            line = line.strip()
            match = regex.match(line)
        
            if match:
                data = match.groupdict()
                u = data['url']
                if u and u not in regex.blacklist:
                    self.timeprocess(lineno, 'Tt', data, self.totaltime)
                    self.timeprocess(lineno, 'Tr', data, self.zopetime)
                    self.timeprocess(lineno, 'Tw', data, self.queuetime)

                    self.strprocess(lineno, 'status', data, self.status)
                    self.strprocess(lineno, 'method', data, self.url)
                    self.strprocess(lineno, 'instance', data, self.instance)
                    self.strprocess(lineno, 'url', data, self.url)
                    self.strprocess(lineno, 'template', data, self.template)

                    tset = self.urltiming.get(u, set())
                    tset.add(int(data['Tr']))
                    self.urltiming[u] = tset
            lineno += 1

        f.close()

        print 'Found %s URLs and %s templates in %s seconds' % (len(self.url), len(self.template), (time.time()-start))

        d = globals()
        d.update(locals())
        i = code.InteractiveConsole(d)
        message  = "Interactive console"
        i.interact(message)


    def slowest(self, number=5):
        for t,s1 in self.totaltime.items()[-number:]:
            print self.gettime(t)
            for u,s2 in self.url.items():
                slow = s1.intersection(s2)
                if slow:
                    print '%s slower than %s for %s' % (len(slow), self.gettime(t), u)

    def tophits(self, number=20):
        topurls = []
        for u,s in self.url.items():
            topurls.append((len(s),u))
        topurls.sort()
        topurls.reverse()
        for n, u in topurls[:number]:
            print '%s\t%s' % (n, u)

    def slowavg(self, number=50, threshold=0):
        urls = []
        for u,ts in self.urltiming.items():
            count = len(ts)
            avg = sum(ts)/count
            urls.append((avg,count,u))
        urls.sort()
        urls.reverse()
        i = 0
        for a, n, u in urls:
            if n>threshold:
                print '% 7d\t% 5d\t%s' % (a, n, u)
                i += 1
                if i >= number:
                    break

    def responsestatus(self):
        for code,s in self.status.items():
            print '%s: %s' % (code, len(s))


def main():
    regex = logparser()

    parser = OptionParser(usage=USAGE)
    parser.add_option('-v', '--verbose', action='count',
                      help='Be more verbose, can be specified twice')
    parser.add_option('-q', '--quiet', action='store_true',
                      help='Shut up completely')
    parser.add_option('-f', '--filename', action='store',
                      help='Read input file.')
    parser.add_option('-m', '--monitor', action='store_true',
                      help='Monitor log')
    parser.add_option('-b', '--beginning', action='store_true',
                      help='Read log from beginning for monitoring')
    parser.add_option('-i', '--interactive', action='store_true',
                      help='Interactive mode')
    parser.add_option('-o', '--output', action='store',
                      help='Write output to CSV file')
    parser.add_option('-a', '--headers', action='store',
                      help='CSV table headers, comma separated, options are: %s' % ', '.join(regex.list_variables()))
    options, args = parser.parse_args()

    if options.verbose and options.quiet:
        parser.error("Can't specify --verbose and --quiet at the same time")

    if options.monitor and (options.interactive or options.output):
        parser.error("Monitor mode can not be combined with interactive or csv modes")

    if options.output and options.interactive:
        parser.error("Can't specify CSV output and interactive at the same time")

    if options.beginning and not options.filename:
        parser.error("You have to define a filename to read log from beginning.")
    
    level = logging.WARNING
    if options.verbose:
        level = logging.INFO
        if options.verbose > 1:
            level = logging.DEBUG
    elif options.quiet:
        level = sys.maxint
    logging.basicConfig(level=level, 
        format='%(asctime)s %(name)s %(message)s',
        datefmt='%H:%M:%S')


    if options.output:
        csvwriter = CSVWriter(options.filename, options.output, options.headers)
        csvwriter.process()

    elif options.interactive:
        interactive = Interactive(options.filename)
        interactive.process()

    elif options.monitor:
        monitor = Monitor(options.filename, options.beginning, options.verbose, options.headers)
        monitor.process()

if __name__ == "__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    main()
