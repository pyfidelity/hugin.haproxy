from hugin.haproxy.logparser import logparser
from hugin.haproxy import keyedfilters

from twisted.internet.protocol import DatagramProtocol
from twisted.web.resource import Resource


class SyslogResource(Resource):
    """The resources wraps and represent a filter in the webserver"""
    def __init__(self, filter_):
        Resource.__init__(self)
        self.filter = filter_

    def render_GET(self, request):
        return '\n'.join(['%s:%.1f' % (k,v) for k,v in self.filter.stats().items()])


class SyslogMonitor(DatagramProtocol):

    def __init__(self, backend=None):
        self.logparser = logparser()
        self.backend = backend

    def datagramReceived(self, data, (host, port)):
        data = self.logparser(data)
        if data is not None:
            if self.backend and data.get('backend') != self.backend:
                return
            for f in keyedfilters.values():
                f.process(data)
