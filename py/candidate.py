import abc
import uuid


class CandidateGenerator:
    def __init__(self, field, pattern_builder):
        self._pattern_builder = pattern_builder
        self._field = field

    @abc.abstractmethod
    def get_candidates(self, document):
        pass


class Candidate(object):
    def __init__(self, line, field, match, hint_line, hint_order, num):
        self.line = line
        self._field = field
        self.match = match
        self.hint_line = hint_line
        self._handler = get_handler(field['type'])
        self.formatted = self._handler.format(match)

        self.hint_order = hint_order
        self.hint_offset_x = hint_line.x0 - line.x0
        self.hint_offset_y = hint_line.y0 - line.x0

        self._id = self._set_id(num)

    def _set_id(self, num):
        try:
            return (self.line.document_id, str(self._line_id(self.line)),
                    str(self._line_id(self.hint_line)), num, self.hint_order)
        except AttributeError:
            return (0, str(self._line_id(self.line)),
                    str(self._line_id(self.hint_line)), num, self.hint_order)

    def _line_id(self, line):
        try:
            if line.id:
                return line.id
            else:
                return line._temp_id
        except AttributeError:
            line._temp_id = uuid.uuid1()
            return line._temp_id

    def id(self):
        return self._id
