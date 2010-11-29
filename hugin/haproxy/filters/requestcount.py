from hugin.haproxy import registerFilter
from operator import itemgetter

LIMIT = 10 # Use 3 * LIMIT internally

class FrequentRequests(object):
    def __init__(self):
        self.limit = LIMIT * 3
        self.urlkey = {} # url -> (count, users)

    def process(self, data):
        url, user = data.get('url', None), data.get('reqcookie', None)
        count, users = self.urlkey.get(url, (0,set()))
        users.add(user)
        self.urlkey[url] = (count + 1, users)

    def stats(self, reset=True, count=20):
        
        stats = self.urlkey

        if reset:
            self.urlkey = {}

        return dict([(url,count) for url,count,users in sorted(stats.items(), key=itemgetter(1), reverse=True)[:LIMIT]])

    def pretty(self, reset=True, count=20):
        stats = self.urlkey

        if reset:
            self.urlkey = {}

        tmp = ['% 6s, % 5s, %s'%(count, len(users), url) for url,(count,users) in sorted(stats.items(), key=itemgetter(1),reverse=True)[:LIMIT]]
        return '\n'.join([' count, users, url'] + tmp)

registerFilter('requestcount', FrequentRequests())
