import numpy

from hugin.haproxy import registerFilter

class TimingAverage(object):
    def __init__(self):
        self.wait = 0
        self.response = 0
        self.total = 0
        self.length = 0

    def process(self, data):
        self.length += 1

        try:
            self.wait += int(data.get('Tw',0)) # We assume there are no -1
        except (TypeError,ValueError):
            pass

        try:
            self.response += int(data.get('Tr',0)) # We assume there are no -1
        except (TypeError,ValueError):
            pass

        try:
            self.total += int(data.get('Tt',0)) # We assume there are no -1
        except (TypeError,ValueError):
            pass

    def stats(self, reset=True):
        wait,response,total,length = self.wait,self.response,self.total,self.length

        if reset:
            self.wait = self.response = self.total = self.length = 0

        if length == 0:
            return dict(wait=0,response=0,total=0)

        return dict(wait=wait/length,
                    response=response/length,
                    total=total/length)

registerFilter('timingaverage', TimingAverage())


class TimingStatistics(object):
    
    def __init__(self):
           self._stats = []

    def process(self, data):

        try:
            self._stats.append(int(data.get("Tt")))
        except (TypeError, ValueError):
            pass

    def stats(self, reset=True):
        stats = numpy.array(self._stats)

        if reset:
            self._stats = []

        ten = median = eighty = ninety = avg = max_ = stddev = 0

        if len(stats):
            length = len(stats)
            stats.sort()
            avg = sum(stats)/length
            max_ = stats[-1]
            ten = stats[min(int(length*10.0/100), length-1)]
            median = stats[min(int(length*50.0/100), length-1)]
            eighty = stats[min(int(length*80.0/100), length-1)]
            ninety = stats[min(int(length*90.0/100), length-1)]
            stddev = numpy.std(stats)

        return dict(ten=ten, median=median, eighty=eighty, ninety=ninety, avg=avg, max=max_, stddev=stddev)

registerFilter('timingstatistics', TimingStatistics())