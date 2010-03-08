from hugin.haproxy import registerFilter
from time import time

class ServiceUnavailable(object):
    """
    Detect http response status that is out of the ordinary. 
    503 might mean we ran out of backends, in which case we should make a list of all the current urls when they finally return
    and possibly also gather info from backends about memory usage, IO etc.
    """
    def __init__(self):
        self.watchlist = set()
        self.backends = {} # backend -> timestamp
        self.unavailable = {} # URL -> count
        self.timeout = None

    def process(self, data):
        instance = data.get('instance', None)

        # Check against watchlist if we have run out of backends - only check for 10 minutes before finalizing report
        if self.watchlist:
            # Limit to 600 seconds
            if self.timeout < time():
                self.watchlist = set()
                self.timeout = None
            # Remove each instance as it becomes available
            # XXX we need some more checking. The status might be 504, or backend response time -1 and code sH-- 
            # which means the request failed or timed out somehow. The URL might be interesting especially if it failed.
            # If the Tt duration indicates that the request was started after the NOSRV failure was seen, it's not interesting.
            elif instance in self.watchlist:
                url = data.get('url', None)
                if url is not None:
                    urlcount = self.unavailable.get(url, 0)
                    urlcount += 1
                    self.unavailable[url] = urlcount
                self.watchlist.remove(instance)

            # This is where we'd send mail or other notification
            if not self.watchlist:
                pass

        # Check if we've run out of backends
        elif data.get('status') in (503, '503') and instance == '<NOSRV>':
            # Keep track of urls and response times as nodes come back up.
            # Watch for nodes that have been active the last 600 seconds
            threshold = int(time()) - 600
            self.watchlist = set([k for k,v in self.backends.items() if v > threshold])
            self.timeout = time()+600
        elif instance is not None:
            # Keep track of current backends with id -> timestamp of access - this becomes watchlist
            self.backends[instance] = time()

    def stats(self, reset=True, count=20):
        unavailable = self.unavailable

        if reset:
            self.watchlist = set()
            self.unavailable = {}
            self.timeout = None

        # Sort on count, return top 20
        # This little gem of obfuscated python sorts the urls based on occuranse, slices count and puts back in dict
        return dict([(k,v) for v,k in sorted([(v,k) for k,v in unavailable.items()])[:count]])

registerFilter('serviceunavailable', ServiceUnavailable())