Hugin HAProxy  monitor
======================

The hugin HAProxy monitor is a daemon that processes HAProxy logs.

The results can be used by munin, or it might trigger alarms.

Twisted setup
=============

Hugin uses twisted for network services. The example startup
script is monitor.tac which starts the syslog listener on port 1514
and the web service on port 10514. The web service consists of resources
wrapping the filters.

You can create your own based on the example.

.. code-block:: python

  # You can run this .tac file directly with:
  #    twistd -ny monitor.tac

  import os
  from hugin.haproxy.syslog import SyslogMonitor, SyslogResource
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


You can run the example directly from the src directory::

 $ bin/twistd -ny src/hugin.haproxy/hugin/haproxy/monitor.tac

If you point your browser to localhost:10514 you should be able to see the `timingstatistics 
<http://localhost:10514/timingstatistics/>` and `timingaverage 
<http://localhost:10514/timingaverage/>`

Note that the munin statistics are reset on every view.


Configuring HAProxy
===================

For the HAProxy frontend, you have to set up the logging.::

  option httplog
  log 127.0.0.1:1514 local6

You can use any facility, the monitor doesn't care.
