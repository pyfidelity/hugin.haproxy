import re

# XXX BLACKLIST SHOULD BE SET IN CONFIG
blacklist = ('/haproxy-status',)
blacklist = '|'.join(blacklist)
blacklist = '(?!(%s))' % blacklist

syslogdprefix = '(?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+\d{4} \[\S+ \S+] )?'
pattsyslogd = '(?:<(?P<syslog>\d+)>)?(?:\w{3}\s[\s\d]\d \d{2}:\d{2}:\d{2}(?: \S+)? (?P<pid>\S+): )?'
pattinfo = '(?P<ip>\S+) \[(?P<date>\S+)\] (?P<frontend>\S+) (?P<backend>[\w]+)/(?P<instance>\S+) '
patttiming = '(?P<Tq>[-\d]+)/(?P<Tw>[-\d]+)/(?P<Tc>[-\d]+)/(?P<Tr>[-\d]+)/(?P<Tt>[-\d]+) '
patthttp = '(?P<status>\d+) (?P<bytes>\d+) (?P<reqcookie>\S+) (?P<respcookie>\S+) '
pattterm = '(?P<terminationevent>\S)(?P<sessionstate>\S)(?P<pc>\S)(?P<opc>\S) '
pattconn = '(?P<actconn>\d+)/(?P<feconn>\d+)/(?P<beconn>\d+)/(?P<srv_conn>\d+)(/(?P<retries>[-\+\d]+))? '
pattqueue = '(?P<srv_queue>\d+)/(?P<listener_queue>\d+) '
patturl = '"(?P<method>\S+) (?:/VirtualHostBase/.*/VirtualHostRoot)?' + blacklist + '(?P<url>\S*/(?P<template>[^/][^\?]+)?)?(?:\?\S*)? \S+'

class logparser(object):
    def __init__(self):
        self.pattern = syslogdprefix + pattsyslogd + pattinfo + patttiming + patthttp + pattterm + pattconn + pattqueue + patturl + '.*'
        self.regex = re.compile(self.pattern)

    def list_variables(self):
        return re.findall('P<([^>]+)>', self.pattern)

    def __call__(self, line):
        res = self.regex.match(line)
        if res is not None:
            res = res.groupdict()
            for i in ('Tq', 'Tw', 'Tc', 'Tr', 'Tt'):
                try:
                    res[i] = int(res[i])
                except ValueError:
                    pass
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
