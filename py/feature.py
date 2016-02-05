import abc

class Feature:
    def __init__(self, field):
        self._field = field

    @abc.abstractmethod
    def compute(self, candidates):
        pass