import abc


class CandidateFinder:
    def __init__(self, field, fid, pattern_builder):
        self._pattern_builder = pattern_builder
        self.field = field
        self.fid = fid

    @abc.abstractmethod
    def get_candidates(self, document):
        pass


class Candidate(object):
    def __init__(self, line, field, match, finder_id, num):
        self.line = line
        self.field = field
        self.match = match
        self.value = self.field.get_value(match)
        self._finder_id = finder_id

        self.id = self._get_id(num)

    def finder_id(self):
        return self._finder_id

    def _get_id(self, num):
        try:
            return (self.line.document_id, self._finder_id, num)
        except AttributeError:
            return (0, self._finder_id, num)
