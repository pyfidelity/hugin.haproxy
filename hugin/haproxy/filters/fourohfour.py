from hugin.haproxy import registerFilter

class FourOhFour(object):
    def __init__(self):
        self.fourohfour = {} # URL -> count

    def process(self, data):
        if data.get('status') in (404, '404'):
            url = data.get('url')
            self.fourohfour[url] = self.fourohfour.get(url, 0) + 1

    def stats(self, reset=True, count=20):
        
        stats = self.fourohfour

        if reset:
            self.fourohfour = {}

        if len(stats)<count:
            return stats

        tmp = []
        for k,v in stats.iteritems():
            tmp.append((v,k))
        tmp.sort()
        return dict([(k,v) for v,k in tmp[-count:]])

    def pretty(self, reset=True, count=20):
        stats = self.fourohfour

        if reset:
            self.fourohfour = {}

        tmp = []
        for k,v in stats.iteritems():
            tmp.append((v,k))
        tmp.sort()
        return '\n'.join(['count,url'] + ['%s,%s'%(v,k) for v,k in tmp[-count:]])


registerFilter('fourohfour', FourOhFour())
