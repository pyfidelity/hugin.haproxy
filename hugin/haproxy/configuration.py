from ConfigParser import RawConfigParser
import re

from paste.util.multidict import MultiDict

class FilterConfig(RawConfigParser, object):
    
    def __init__(self):
        RawConfigParser.__init__(self, dict_type=MultiDict)
    
    def urls(self):
        output = self._dict()
        for key, value in self._sections.items():
            output[key] = value['method'], value['match']
        return output
    
    def _read(self, *args, **kwargs):
        return_value = RawConfigParser._read(self, *args, **kwargs)
        for key in self._sections.keys():
            self._sections[key]['match'] = re.compile(self._sections[key]['match'])
        return return_value