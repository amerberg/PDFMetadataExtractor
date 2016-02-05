import abc

class Feature:
    def __init__(self, field):
        self.field = field

    @abc.abstractmethod
    def compute(self, candidates):
        pass