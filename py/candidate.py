import abc


class CandidateFinder:
    def __init__(self, field, gid, pattern_builder):
        self._pattern_builder = pattern_builder
        self.field = field
        self.gid = gid

    @abc.abstractmethod
    def get_candidates(self, document):
        pass


class Candidate(object):
    def __init__(self, line, field, match, generator_id, num):
        self.line = line
        self.field = field
        self.match = match
        self.value = self.field.get_value(match)
        self._generator_id = generator_id

        self.id = self._get_id(num)

    def _get_id(self, num):
        try:
            return (self.line.document_id, self._generator_id, num)
        except AttributeError:
            return (0, self._generator_id, num)
