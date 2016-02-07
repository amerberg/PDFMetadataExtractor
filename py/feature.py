import abc

class Feature:
    """An abstract base class for feature types."""
    def __init__(self, field):
        """Keep track of the field this feature belongs to."""
        self.field = field

    @abc.abstractmethod
    def compute(self, candidates):
        """ Compute this feature for a list of candidates.

        :param candidates: A list of candidates.
        :return: A dictionary of feature values, keyed by candidate ID.
        """

        pass