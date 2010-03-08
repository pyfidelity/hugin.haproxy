from hugin.haproxy import registerFilter

LOGSTATUSCODES = ('401', '403', '404', '500', '501', '502', '503', '504')

class StatusStats(object):

    def __init__(self):
        self.statuscount = dict.fromkeys(LOGSTATUSCODES, 0) # status -> count

    def process(self, data):
        status = data.get('status', None)
        if status in LOGSTATUSCODES:
            self.statuscount[status] = self.statuscount.get(status, 0) + 1

    def stats(self, reset=True, count=20):
        statuscount = self.statuscount

        if reset:
            self.statuscount = dict.fromkeys(LOGSTATUSCODES, 0)

        return statuscount

registerFilter('statusstats', StatusStats())