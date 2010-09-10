import unittest
from hugin.haproxy.logparser import logparser

class TestLogParser(unittest.TestCase):

    def setUp(self):
        self.parser = logparser()

    def test_listvariables(self):
        expected = ['syslog', 'pid', 
                    'ip', 'date', 'frontend', 'backend', 'instance',
                    'Tq', 'Tw', 'Tc', 'Tr', 'Tt',
                    'status', 'bytes',
                    'reqcookie', 'respcookie', 
                    'terminationevent', 'sessionstate', 'pc', 'opc',
                    'actconn', 'feconn', 'beconn', 'srv_conn', 'retries', 
                    'srv_queue', 'listener_queue', 'captures',
                    'method', 'url', 'template', 'querystring'
                    ]
        self.failUnlessEqual(self.parser.list_variables(), expected)

    def test_blacklist(self):
        logline = 'Nov  2 14:04:10 localhost.localdomain haproxy[2123]: ' + \
                  '127.0.0.1:41618 [02/Nov/2009:14:04:10.382] frnt bck/inst ' + \
                  '3183/23/-1/12/11215 200 937 BCef - SCVD 1/2/3/4/0 1/30 ' + \
                  '"GET /haproxy-status HTTP/1.1"'

        self.failIf(self.parser(logline))

        logline = 'Nov  2 14:04:10 localhost.localdomain haproxy[2123]: ' + \
                  '127.0.0.1:41618 [02/Nov/2009:14:04:10.382] frnt bck/inst ' + \
                  '3183/23/-1/12/11215 200 937 BCef - SCVD 1/2/3/4/0 1/30 ' + \
                  '"GET /haproxy-status?norefresh HTTP/1.1"'
        self.failIf(self.parser(logline))


    def test_basiclogline1(self):
        logline = 'Nov  2 14:04:10 localhost.localdomain haproxy[2123]: ' + \
                  '127.0.0.1:41618 [02/Nov/2009:14:04:10.382] frnt bck-1/inst ' + \
                  '3183/23/-1/12/11215 200 937 BCef - SCVD 1/2/3/4/0 1/30 ' + \
                  '"GET /VirtualHostBase/http/www.website.org:80/plone/VirtualHostRoot/bullet.gif HTTP/1.1"'

        expect = {'syslog':None,
                  'pid':'haproxy[2123]',
                  'ip': '127.0.0.1:41618', 
                  'date': '02/Nov/2009:14:04:10.382', 
                  'frontend': 'frnt',
                  'backend': 'bck-1', 
                  'instance': 'inst', 
                  'Tq': 3183, 
                  'Tw': 23, 
                  'Tc': -1, 
                  'Tr': 12, 
                  'Tt': 11215, 
                  'status': '200', 
                  'bytes': '937', 
                  'reqcookie': 'BCef', 
                  'respcookie': '-', 
                  'terminationevent': 'S', 
                  'sessionstate': 'C',
                  'pc': 'V', 
                  'opc': 'D', 
                  'actconn': '1', 
                  'feconn': '2', 
                  'beconn': '3', 
                  'srv_conn': '4', 
                  'retries': '0', 
                  'srv_queue': '1', 
                  'listener_queue': '30', 
                  'captures': None,
                  'method': 'GET', 
                  'url': '/bullet.gif', 
                  'template': 'bullet.gif', 
                  'querystring': None,
                  }

        res = self.parser(logline)
        self.failUnlessEqual(res, expect, ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))

    def test_basiclogline2(self):
        logline = 'Nov  2 14:04:10 localhost.localdomain haproxy[2123]: ' + \
                  '127.0.0.1:41618 [02/Nov/2009:14:04:10.382] frnt bck-1/inst ' + \
                  '3183/23/-1/12/11215 200 937 BCef - SCVD 1/2/3/4/0 1/30 ' + \
                  '"GET /VirtualHostBase/http/www.website.org:80/plone/VirtualHostRoot/search?query=foo HTTP/1.1"'

        expect = {'syslog':None,
                  'pid':'haproxy[2123]',
                  'ip': '127.0.0.1:41618', 
                  'date': '02/Nov/2009:14:04:10.382', 
                  'frontend': 'frnt',
                  'backend': 'bck-1', 
                  'instance': 'inst', 
                  'Tq': 3183, 
                  'Tw': 23, 
                  'Tc': -1, 
                  'Tr': 12, 
                  'Tt': 11215, 
                  'status': '200', 
                  'bytes': '937', 
                  'reqcookie': 'BCef', 
                  'respcookie': '-', 
                  'terminationevent': 'S', 
                  'sessionstate': 'C',
                  'pc': 'V', 
                  'opc': 'D', 
                  'actconn': '1', 
                  'feconn': '2', 
                  'beconn': '3', 
                  'srv_conn': '4', 
                  'retries': '0', 
                  'srv_queue': '1', 
                  'listener_queue': '30', 
                  'captures': None,
                  'method': 'GET', 
                  'url': '/search', 
                  'template': 'search', 
                  'querystring': "?query=foo",
                  }

        res = self.parser(logline)
        self.failUnlessEqual(res, expect, ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))


    def test_syslogline1(self):
        logline = '<182>Nov  3 14:12:50 haproxy[30111]: ' + \
                  '127.0.0.1:61686 [03/Nov/2009:14:12:50.109] frnt bck/inst ' + \
                  '0/0/0/5/6 200 2931 - - ---- 0/0/0/0/0 0/0 "GET / HTTP/1.1"\n'

        expect = {'syslog':'182',
                  'pid':'haproxy[30111]',
                  'ip': '127.0.0.1:61686', 
                  'date': '03/Nov/2009:14:12:50.109', 
                  'frontend': 'frnt',
                  'backend': 'bck', 
                  'instance': 'inst', 
                  'Tq': 0, 
                  'Tw': 0, 
                  'Tc': 0, 
                  'Tr': 5, 
                  'Tt': 6, 
                  'status': '200', 
                  'bytes': '2931', 
                  'reqcookie': '-', 
                  'respcookie': '-', 
                  'terminationevent': '-', 
                  'sessionstate': '-',
                  'pc': '-', 
                  'opc': '-', 
                  'actconn': '0', 
                  'feconn': '0', 
                  'beconn': '0', 
                  'srv_conn': '0', 
                  'retries': '0', 
                  'srv_queue': '0', 
                  'listener_queue': '0', 
                  'captures': None,
                  'method': 'GET', 
                  'url': '/', 
                  'template': None, 
                  'querystring': None,
                  }

        res = self.parser(logline)
        self.failUnlessEqual(res, expect, ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))

    def test_syslogline2(self):
        logline = '<182>Nov  2 14:04:10 localhost.localdomain haproxy[2123]: ' + \
                  '127.0.0.1:41618 [02/Nov/2009:14:04:10.382] frnt bck/inst ' + \
                  '3183/23/-1/12/11215 200 937 BCef - SCVD 1/2/3/4/0 1/30 ' + \
                  '"GET /VirtualHostBase/http/www.website.org:80/plone/VirtualHostRoot/bullet.gif HTTP/1.1"\n'

        expect = {'syslog':'182',
                  'pid':'haproxy[2123]',
                  'ip': '127.0.0.1:41618', 
                  'date': '02/Nov/2009:14:04:10.382', 
                  'frontend': 'frnt',
                  'backend': 'bck', 
                  'instance': 'inst', 
                  'Tq': 3183, 
                  'Tw': 23, 
                  'Tc': -1, 
                  'Tr': 12, 
                  'Tt': 11215, 
                  'status': '200', 
                  'bytes': '937', 
                  'reqcookie': 'BCef', 
                  'respcookie': '-', 
                  'terminationevent': 'S', 
                  'sessionstate': 'C',
                  'pc': 'V', 
                  'opc': 'D', 
                  'actconn': '1', 
                  'feconn': '2', 
                  'beconn': '3', 
                  'srv_conn': '4', 
                  'retries': '0', 
                  'srv_queue': '1', 
                  'listener_queue': '30', 
                  'captures': None,
                  'method': 'GET', 
                  'url': '/bullet.gif', 
                  'template': 'bullet.gif', 
                  'querystring': None,
                  }

        res = self.parser(logline)
        self.failUnlessEqual(res, expect, ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))

    def test_syslogline3(self):
        logline = '2009-12-15 23:14:19+0100 [hugin.haproxy.syslog.SyslogMonitor (UDP)] '+\
                  '<182>Dec 15 23:14:19 haproxy[4991]: '+\
                  '127.0.0.1:50840 [15/Dec/2009:23:14:19.416] zopecluster zope/plone0203 '+\
                  '0/0/0/241/244 200 3402 - - ---- 0/0/0/0/0 0/0 '+\
                  '"GET /VirtualHostBase/http/www.website.com:80/plone/VirtualHostRoot/frontpage_view HTTP/1.1"'

        expect = {'syslog':'182',
                  'pid':'haproxy[4991]',
                  'ip': '127.0.0.1:50840', 
                  'date': '15/Dec/2009:23:14:19.416', 
                  'frontend': 'zopecluster',
                  'backend': 'zope', 
                  'instance': 'plone0203', 
                  'Tq': 0, 
                  'Tw': 0, 
                  'Tc': 0, 
                  'Tr': 241, 
                  'Tt': 244, 
                  'status': '200', 
                  'bytes': '3402', 
                  'reqcookie': '-', 
                  'respcookie': '-', 
                  'terminationevent': '-', 
                  'sessionstate': '-',
                  'pc': '-', 
                  'opc': '-', 
                  'actconn': '0', 
                  'feconn': '0', 
                  'beconn': '0', 
                  'srv_conn': '0', 
                  'retries': '0', 
                  'srv_queue': '0', 
                  'listener_queue': '0', 
                  'captures': None,
                  'method': 'GET', 
                  'url': '/frontpage_view', 
                  'template': 'frontpage_view', 
                  'querystring': None,
                  }

        res = self.parser(logline)
        self.failUnlessEqual(res, expect, ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))

    def test_syslogline4(self):
        logline = 'Jan  1 07:05:18 localhost haproxy[4145]: '+\
                  '127.0.0.1:41760 [01/Jan/2010:07:05:17.469] public public/public06 '+\
                  '0/0/0/1379/1380 200 482 - - ---- 0/0/0/0 0/0 '+\
                  '"GET /web/MMBase/http/www.site.no:80/249934 HTTP/1.1" '

        expect = {'syslog':None,
                  'pid':'haproxy[4145]',
                  'ip': '127.0.0.1:41760', 
                  'date': '01/Jan/2010:07:05:17.469',
                  'frontend': 'public',
                  'backend': 'public', 
                  'instance': 'public06', 
                  'Tq': 0, 
                  'Tw': 0, 
                  'Tc': 0, 
                  'Tr': 1379, 
                  'Tt': 1380, 
                  'status': '200', 
                  'bytes': '482', 
                  'reqcookie': '-', 
                  'respcookie': '-', 
                  'terminationevent': '-', 
                  'sessionstate': '-',
                  'pc': '-', 
                  'opc': '-', 
                  'actconn': '0', 
                  'feconn': '0', 
                  'beconn': '0', 
                  'srv_conn': '0', 
                  'retries': None, 
                  'srv_queue': '0', 
                  'listener_queue': '0', 
                  'captures': None,
                  'method': 'GET', 
                  'url': '/web/MMBase/http/www.site.no:80/249934', 
                  'template': '249934', 
                  'querystring': None,
                  }

        res = self.parser(logline)
        self.failUnlessEqual(res, expect, ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))

    def test_syslogline_with_captured_header(self):
        logline = 'Jan  1 07:05:18 localhost haproxy[4145]: '+\
                  '127.0.0.1:41760 [01/Jan/2010:07:05:17.469] public public/public06 '+\
                  '0/0/0/1379/1380 200 482 - - ---- 0/0/0/0 0/0 {foo} '+\
                  '"GET /web/MMBase/http/www.site.no:80/249934 HTTP/1.1" '

        expect = {'syslog':None,
                  'pid':'haproxy[4145]',
                  'ip': '127.0.0.1:41760',
                  'date': '01/Jan/2010:07:05:17.469',
                  'frontend': 'public',
                  'backend': 'public',
                  'instance': 'public06',
                  'Tq': 0,
                  'Tw': 0,
                  'Tc': 0,
                  'Tr': 1379,
                  'Tt': 1380,
                  'status': '200',
                  'bytes': '482',
                  'reqcookie': '-',
                  'respcookie': '-',
                  'terminationevent': '-',
                  'sessionstate': '-',
                  'pc': '-',
                  'opc': '-',
                  'actconn': '0',
                  'feconn': '0',
                  'beconn': '0',
                  'srv_conn': '0',
                  'retries': None,
                  'srv_queue': '0',
                  'listener_queue': '0',
                  'captures': 'foo',
                  'method': 'GET',
                  'url': '/web/MMBase/http/www.site.no:80/249934',
                  'template': '249934',
                  'querystring': None,
                  }

        res = self.parser(logline)
        self.failUnlessEqual(res, expect, ', '.join(['%s: %s != %s' % (k,v,expect[k]) for k,v in res.items() if expect[k] != v]))
