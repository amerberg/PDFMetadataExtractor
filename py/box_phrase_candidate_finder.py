from candidate import CandidateFinder, Candidate
import re

MAX_LENGTH = 10000

class BoxPhraseCandidateFinder(CandidateFinder):
    """Find candidates by presence of certain phrases in their box."""
    def __init__(self, field, fid, phrases, candidate_lines,
                 bbox=None, min_height=0, max_height=MAX_LENGTH, min_width=0,
                 max_width=MAX_LENGTH, min_page=0, max_page=None):
        """ Set parameters for the candidate search.

        :param field: The field to search for.
        :param fid: The finder id of this object.
        :param phrases: The phrases to look for in the box.
        :param candidate_lines: The indices of the lines to be designated
         candidates.
        :param bbox: The bounding box within which to search.
        :param min_height: The minimum height box to consider.
        :param max_height: The maximum height box to consider.
        :param min_width: The minimum width box to consider.
        :param max_width: The maximum width box to consider.
        :param min_page: The minimum page number to look on.
        :param max_height: The maximum page number to look on.
        """
        self._phrases = phrases
        self._candidate_lines = candidate_lines
        self._counts = {}
        self._min_height = min_height
        self._max_height = max_height
        self._min_width = min_width
        self._max_width = max_width
        self._min_page = min_page
        self._max_page = max_page
        self._bbox = bbox if bbox else [0, 0, MAX_LENGTH, MAX_LENGTH]
        CandidateFinder.__init__(self, field, fid)

    def _boxes_in_bbox(self, document):
        """"Get all boxes in the bounding box for this document"""
        bbox = self._bbox
        boxes = document.get_boxes()
        return [box for box in boxes if bbox[0] <= box.x0 and
                box.x1 <= bbox[2] and bbox[1] <= box.y0 and
                box.y1 <= bbox[3] and self._allowed_page(box)]

    def _allowed_page(self, box):
        """Determine whether a given box is on a page within search bounds."""
        if self._max_page:
            return self._min_page < box.page < self._max_page
        else:
            return self._min_page < box.page

    def _has_phrase(self, box):
        """Determine whether a box has the sought phrases."""
        lines = box.get_lines()
        pattern = self.field.settings.pattern_builder.list_pattern(self._phrases)
        for line in lines:
            if re.search(pattern, line.text) is not None:
                return True
        return False

    def get_candidates(self, document):
        """Get all candidates for a document."""
        if not hasattr(document, "id"):
            document.id = 0
        self._counts[document.id] = 0

        strip_labels = self.field.settings.strip_labels
        field = self.field

        boxes = [box for box in self._boxes_in_bbox(document)
                 if self._has_phrase(box)]

        key = lambda l: (-l.y0, l.x0)
        candidates = []
        for box in boxes:
            lines = sorted(box.get_lines(), key=key)
            for index in self._candidate_lines:
                try:
                    line = lines[index]
                    stripped = strip_labels(line.text)
                    preprocessed = [field.preprocess(text) for text in stripped]
                    matches = [field.find_value(text) for text in preprocessed]
                    if len(matches):
                        candidates.append(Candidate(line, field, matches[0], self.fid, self._counts[document.id]))
                except (IndexError, TypeError):
                    # No such line exists in this box! Don't produce a candidate.
                    pass

        return candidates
