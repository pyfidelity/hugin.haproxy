from ConfigParser import RawConfigParser
import re

class FilterConfig(RawConfigParser, object):
    
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