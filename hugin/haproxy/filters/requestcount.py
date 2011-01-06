import re
from hugin.haproxy import registerFilter
from operator import itemgetter

LIMIT = 10 # Use 3 * LIMIT internally

IGNORE = re.compile('(^/_log.*|^/lo(gin_f(orm|ailed)|gged_out|gout).*|^/eli/@@whoami|^/@@(idmintegration|esi/|frontpage_view).*|^/acl_users/.*|^/portal_[^/]+/|(/[^/]+)*/(portlet_image|image(_\S+)?|@@r(ight-column|efreshPortlet)|[^/]+\.(css|gif|jpg|jpeg|png|pdf|kss|js|xls|xsl|doc)))')

REGIONSANDCHAINS = '(nordic|(central|southern)-europe|uk)/(elkjop[^/]*|lefdal[^/]*|elgigant[^/]+|electro[^/]+|unieuro|dsg[^/]+|gigantti[^/]*|pc-[^/]*)'

REWRITE = re.compile('^(/%s)?(?P<url>/[^\?]*)(\?.*)?' % REGIONSANDCHAINS)

FRONTPAGE = re.compile('^/%s$' % REGIONSANDCHAINS)

class FrequentRequests(object):
    def __init__(self):
        self.limit = LIMIT * 3
        self.urlkey = {} # url -> (count, users)

    def process(self, data):
        url, user = data.get('url', None), data.get('reqcookie', None)
        if IGNORE.match(url):
            return # Bail immediately on irrelevant URLs
        url = REWRITE.sub('\g<url>', url) # This enables us to see clearer what is used across chains

        if FRONTPAGE.match(url):
            return # Not interested in chain frontpages

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
