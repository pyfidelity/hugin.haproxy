import re
from hugin.haproxy import registerFilter

LIMIT = 10 # Use 3 * LIMIT internally

IGNORE = re.compile('(^/_log.*|^/lo(gin_f(orm|ailed)|gged_out|gout).*|^/eli/@@whoami|^/@@(idmintegration|esi/|frontpage_view).*|^/acl_users/.*|^/portal_[^/]+/|(/[^/]+)*/(portlet_image|image(_\S+)?|@@r(ight-column|efreshPortlet)|[^/]+\.(css|gif|jpg|jpeg|png|pdf|kss|js|xls|xsl|doc)))')

REGIONSANDCHAINS = '(nordic|(central|southern)-europe|uk)/(elkjop[^/]*|lefdal[^/]*|elgigant[^/]+|electro[^/]+|unieuro|dsg[^/]+|gigantti[^/]*|pc-[^/]*)'

REWRITE = re.compile('^(/%s)?(?P<url>/[^\?]*)(\?.*)?' % REGIONSANDCHAINS)

FRONTPAGE = re.compile('^/%s$' % REGIONSANDCHAINS)

class ClickPath(object):
    def __init__(self):
        self.limit = LIMIT * 3
        self.userkey = {} # user -> [(url,time),]

    def process(self, data):
        user,url,date = data.get('reqcookie', None), data.get('url', None), data.get('date', None)
        if IGNORE.match(url):
            return # Bail immediately on irrelevant URLs
        url = REWRITE.sub('\g<url>', url) # This enables us to see clearer what is used across chains

        if user:
            urls = self.userkey.get(user, [])
            urls.append((url,date))
            self.userkey[user] = urls

    def stats(self, reset=True, count=20):
        
        stats = self.userkey

        if reset:
            self.userkey = {}

        return dict([(user,len(urls)) for user,urls in sorted(stats.items(), key=lambda x:len(x[1]), reverse=True)[:LIMIT]])

    def pretty(self, reset=True, count=20):
        stats = self.userkey

        if reset:
            self.userkey = {}

        out = []
        for user,urls in sorted(stats.items(), key=lambda x:len(x[1]), reverse=True)[:LIMIT]:
            out.append(user)
            prevurl = None
            for url,date in urls:
                if url == prevurl:
                    continue
                else:
                    prevurl = url
                out.append('  %s %s' % (date, url))
        return '\n'.join(out)

registerFilter('clickpath', ClickPath())
