from hugin.haproxy import registerFilter

LIMIT = 10 # Use 3 * LIMIT internally
THRESHOLD = 5000

class SlowestRequests(object):
    def __init__(self):
        self.limit = LIMIT * 3
        self.threshold = THRESHOLD # Used for quick comparison of current slowest response time
        self.slowest = [] # list of [slowest, url, [list,of,responsetimes]]
        self.urlkey = {}

    def process(self, data):
        time, url = data.get('Tr', 0), data.get('url', None)
        if time > self.threshold or self.urlkey.has_key(url):
            entry = self.urlkey.get(url, None)
            if entry is None:
                entry = [time, url, [time]]
                self.urlkey[url] = entry
                self.slowest.append(entry)
            else:
                entry[2].append(time)
                if time > entry[0]:
                    entry[0] = time
            self.slowest.sort()
            self.slowest.reverse()
            try:
                self.threshold = self.slowest[30][0]
            except IndexError:
                self.threshold = self.slowest[-1][0]

    def stats(self, reset=True, count=20):
        
        stats = self.slowest

        if reset:
            self.threshold = THRESHOLD
            self.slowest = []
            self.urlkey = {}

        #for slowest, url, times in stats[:LIMIT]:
        #    print slowest, url, sum(times)/len(times)

        #res = {}
        #for slowest, url, times in stats[:LIMIT]:
        #    res[url] = '%s (%s)' % (slowest, sum(times)/len(times))
        #return res
        return dict([(url, slowest) for slowest,url,times in stats[:LIMIT]])

    def pretty(self, reset=True, count=20):
        stats = self.slowest

        if reset:
            self.threshold = THRESHOLD
            self.slowest = []
            self.urlkey = {}

        tmp = ['%s,%s,%s'%(slowest,url,(sum(times)/len(times))) for slowest,url,times in stats[:LIMIT]]
        return '\n'.join(['slowest,url,avg'] + tmp)

registerFilter('slowestrequests', SlowestRequests())
