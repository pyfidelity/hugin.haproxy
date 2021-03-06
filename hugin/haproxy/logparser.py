import re, warnings

# XXX BLACKLIST SHOULD BE SET IN CONFIG
blacklist = ('/haproxy-status',)
blacklist = '|'.join(blacklist)

syslogdprefix = '(?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+\d{4} \[\S+ \S+] )?'
pattsyslogd = '(?:<(?P<syslog>\d+)>)?(?:\w{3}\s[\s\d]\d \d{2}:\d{2}:\d{2}(?: \S+)? (?P<pid>\S+): )?'
pattinfo = '(?P<ip>\S+) \[(?P<date>\S+)\] (?P<frontend>\S+) (?P<backend>[\w-]+)/(?P<instance>\S+) '
patttiming = '(?P<Tq>[-\d]+)/(?P<Tw>[-\d]+)/(?P<Tc>[-\d]+)/(?P<Tr>[-\d]+)/(?P<Tt>[-\d]+) '
patthttp = '(?P<status>\d+) (?P<bytes>\d+) (?P<reqcookie>\S+) (?P<respcookie>\S+) '
pattterm = '(?P<terminationevent>\S)(?P<sessionstate>\S)(?P<pc>\S)(?P<opc>\S) '
pattconn = '(?P<actconn>\d+)/(?P<feconn>\d+)/(?P<beconn>\d+)/(?P<srv_conn>\d+)(/(?P<retries>[-\+\d]+))? '
pattqueue = '(?P<srv_queue>\d+)/(?P<listener_queue>\d+) '
pattcaptures = '({(?P<captures>[^}]*)\} )?'
patturl = '"(?P<method>\S+) (?:/VirtualHostBase/.*/VirtualHostRoot)?' + '(?P<url>\S*/(?P<template>[^/][^\?]+)?)?(?P<querystring>\?\S*)? \S+"'

DATE_FORMAT = "%d/%b/%Y:%H:%M:%S.%f"

class logparser(object):
    def __init__(self):
        self.pattern = syslogdprefix + pattsyslogd + pattinfo + patttiming + patthttp + pattterm + pattconn + pattqueue + pattcaptures + patturl
        self.regex = re.compile(self.pattern)
        self.blacklist = re.compile(blacklist)

    def list_variables(self):
        return re.findall('P<([^>]+)>', self.pattern)

    def __call__(self, line):
        line = line.rstrip()
        if not line.endswith('"'):
            # the url always ends with a doublequote, if that's not the case
            # then the log entry was cut off due to size limits and we try
            # to make it matchable with the following line
            line = '%s HTTP/1.1"' % line
        res = self.regex.match(line)
        if res is not None:
            res = res.groupdict()
            if self.blacklist.match(res['url']):
                return
            for i in ('Tq', 'Tw', 'Tc', 'Tr', 'Tt'):
                try:
                    res[i] = int(res[i])
                except ValueError:
                    pass
        else:
            warnings.warn("Couldn't match %s" % line)
        return res

class partiallogparser(object):
    def __call__(self, line):
        comp = line.split(' ')

        if len(comp)<10:
            return dict()

        # url = comp[-2]
        # srv_queue, listener_queue = comp[-4].split('/')
        # actconn, feconn, beconn, srv_conn, retries = comp[-5].split('/')
        # terminationevent, sessionstate, pc, opc = comp[-6]
        # respcookie = comp[-7]
        # reqcookie = comp[-8]
        # bytes = comp[-9]
        # status = comp[-10]
        Tq, Tw, Tc, Tr, Tt = comp[-11].split('/')
        backend,instance = comp[-12].split('/')
        frontend = comp[-13]
        return dict(url=comp[-2],
                    Tw=int(Tw),
                    Tr=int(Tr),
                    Tt=int(Tt),
                    backend=backend,
                    instance=instance,
                    frontend=frontend)
