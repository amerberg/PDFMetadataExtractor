from candidate import CandidateFinder, Candidate
from feature import Feature
import re

class BoxPhraseCandidateFinder(CandidateFinder):
    """Find candidates by presence of phrases in their box.


    """
    def __init__(self, field, fid, phrases, candidate_lines,
                 bbox=None, min_height=0, max_height=10000, min_width=0,
                 max_width=10000, min_page=0, max_page=None):
        self._phrases = phrases
        self._candidate_lines = candidate_lines
        self._counts = {}
        self._min_height = min_height
        self._max_height = max_height
        self._min_width = min_width
        self._max_width = max_width
        self._min_page = min_page
        self._max_page = max_page
        self._bbox = bbox if bbox else [0, 0, 10000, 10000]
        CandidateFinder.__init__(self, field, fid)

    def _boxes_in_bbox(self, document):
        """"Get all boxes in the bounding box for this document"""
        bbox = self._bbox
        boxes = document.get_boxes()
        return [box for box in boxes if bbox[0] <= box.x0 and
                box.x1 <= bbox[2] and bbox[1] <= box.y0 and
                box.y1 <= bbox[3] and self._allowed_page(box)]

    def _allowed_page(self, box):
        if self._max_page:
            return self._min_page < box.page < self._max_page
        else:
            return self._min_page < box.page

    def _has_phrase(self, box):
        lines = box.get_lines()
        pattern = self.field.settings.pattern_builder.list_pattern(self._phrases)
        for line in lines:
            if re.search(pattern, line.text) is not None:
                return True
        return False

    def get_candidates(self, document):
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


class LabelCandidate(Candidate):
    def __init__(self, line, field, match, generator_id, num, label_line):
        self.label_line = label_line
        self.label_offset_x = label_line.x0 - line.x0
        self.label_offset_y = label_line.y0 - line.x0
        Candidate.__init__(self, line, field, match, generator_id, num)

class LabelOffsetX(Feature):
    def compute(self, candidates):
        offsets = {}
        for candidate in candidates:
            if isinstance(candidate, LabelCandidate):
                offsets[candidate.id] = candidate.label_line.x0 - candidate.line.x0
            else:
                offsets[candidate.id] = 0
        return offsets

class LabelOffsetY(Feature):
    def compute(self, candidates):
        offsets = {}
        for candidate in candidates:
            if isinstance(candidate, LabelCandidate):
                offsets[candidate.id] = candidate.label_line.y0 - candidate.line.y0
            else:
                offsets[candidate.id] = 0
        return offsets