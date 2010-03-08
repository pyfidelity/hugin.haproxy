# Hey presto, a module

keyedfilters = dict()

def registerFilter(key, filter_):
    keyedfilters[key] = filter_

def unregisterFilter(key):
    if keyedfilters.has_key(key):
        del keyedfilters[key]