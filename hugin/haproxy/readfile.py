from hugin.haproxy.logparser import logparser

from hugin.haproxy.filters import timingstats
from hugin.haproxy.filters import fourohfour
from hugin.haproxy.filters import slowestrequests
from hugin.haproxy.filters import userstate
from hugin.haproxy.filters import statusalarm
from hugin.haproxy.filters import statusstats
from hugin.haproxy.filters import requestcount
from hugin.haproxy.filters import clickpath


from hugin.haproxy import keyedfilters

from fileinput import input
from optparse import OptionParser

import logging
import time

USAGE = """\
usage: %%prog [options]

readfile parses HAProxy logs
"""


def main():

    parser = OptionParser(usage=USAGE)
    parser.add_option('-v', '--verbose', action='count',
                      help='Be more verbose, can be specified twice')
    parser.add_option('-q', '--quiet', action='store_true',
                      help='Shut up completely')
    parser.add_option('-f', '--filename', action='store',
                      help='Read input file.')
    parser.add_option('-b', '--backend', action='store',
                      help='Limit to backend.')
    parser.add_option('-H', '--perhour', action='store_true',
                      help='Print stats per hour.')
    parser.add_option('-m', '--muninfilters', action='store',
                      help='Comma separated list of filters to use with perhour.')
    options, args = parser.parse_args()

    if options.verbose and options.quiet:
        parser.error("Can't specify --verbose and --quiet at the same time")
    
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

    backend = options.backend
    perhour = options.perhour
    if options.muninfilters:
        muninfilters = options.muninfilters.split(',')
    else:
        muninfilters = ('userstate','timingaverage','timingstatistics','slowestrequests')
    regex = logparser()

    def printstats(allfilters=True):
        if allfilters:
            kf = keyedfilters.items()
        else:
            kf = [(k,keyedfilters[k]) for k in muninfilters]
        for k,f in kf:
            try:
                res = f.pretty()
                print k, '\n', res
            except AttributeError:
                print k, ',\t'.join(['%s:%d' % (k,v) for k,v in f.stats().items()])


    f = input(filter(None, [options.filename]))
    start = time.time()
    count = 0
    hour = 0
    for line in f:
        count+=1
        data = regex(line)
        if data is not None:
            if not backend or backend == data.get('backend', None):

                # Print stats if printing each hour
                if perhour:
                    date = data.get('date', None)
                    if date is not None and date[12:14] != hour and 0 < (int(date[12:14])-int(hour))%24 < 12:
                        print'============================'
                        print date[:17]
                        hour = date[12:14]
                        printstats(allfilters=False)

                for f in keyedfilters.values():
                    f.process(data)
    duration = time.time() - start
    print "Processed %s entries in %.1f seconds (%d entries/second)" % (count, duration, count/duration)

    printstats(allfilters=True)

if __name__ == "__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    main()
