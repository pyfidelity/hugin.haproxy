# Userstate is about detecting when users switch backend node when session affinity is used.
import re
from hugin.haproxy import registerFilter
from collections import deque

COOKIEMATCH = re.compile('.*="?(?P<cookie>\S+)')

class UserState(object):

    def __init__(self):
        self.duplicates = 0 # Redundant reloads where user press stop or reload
        self.redispatch = 0 # Session affinity redispatch
        self.affinity = 0 # Session affinity where previous 4 request were to the same instance
        self.status = {} # Keep track of last 4 requests for each uid

    def process(self, data):
        #match = COOKIEMATCH.match(data['reqcookie'])
        #if match:
        #    uid = match.group('cookie')
        reqcookie = data.get('reqcookie', None)
        if reqcookie is not None and len(reqcookie) > 1:
            uid = reqcookie[6:] # __ac="cookieval...
            hist = self.status.get(uid, deque(maxlen=4)) # We keep track of the 4 last requests

            previous = hist and hist[0]
            instance = data['instance']

            if previous:
                # Detect redundant reloads - C is client abort
                if previous['terminationevent'] == 'C' and previous['url'] == data['url']:
                    self.duplicates += 1

                # Check for session affinity
                if previous['instance'] == instance:
                    for item in hist:
                        if item['instance'] != instance:
                            break # Different instance, no affinity
                    self.affinity += 1
                # We only check for redispatch or affinity if we have a full history
                elif len(hist) == 4:
                    # Check for redispatch
                    instances = set([h['instance'] for h in hist])
                    if len(instances) == 1:
                        self.redispatch += 1


            hist.appendleft(dict(url=data['url'], 
                                 terminationevent=data['terminationevent'],
                                 instance=instance,))
            self.status[uid] = hist

        return data

    def stats(self, reset=True, count=20):
        duplicates, redispatch, affinity = self.duplicates, self.redispatch, self.affinity

        if reset:
            self.duplicates = self.redispatch = self.affinity = 0

        return dict(duplicates=duplicates,
                    redispatch=redispatch,
                    affinity=affinity)

registerFilter('userstate', UserState())
