# You can run this .tac file directly with:
#    twistd -ny monitor.tac

import os
from hugin.haproxy.syslog import SyslogMonitor, SyslogResource

from hugin.haproxy.filters import timingstats
from hugin.haproxy.filters import fourohfour
from hugin.haproxy.filters import userstate
from hugin.haproxy.filters import slowestrequests
from hugin.haproxy.filters import statusalarm
from hugin.haproxy.filters import statusstats

from hugin.haproxy import keyedfilters

from twisted.application import service, internet
from twisted.internet.protocol import ServerFactory
from twisted.web import static, server
from twisted.web.server import Site
from twisted.web.resource import Resource

application = service.Application("HAProxy monitor")

service = internet.UDPServer(1514, SyslogMonitor())
service.setServiceParent(application)

root = Resource()

for path,flt in keyedfilters.items():
    root.putChild(path, SyslogResource(flt))

factory = Site(root)
service = internet.TCPServer(10514, factory)
service.setServiceParent(application)
