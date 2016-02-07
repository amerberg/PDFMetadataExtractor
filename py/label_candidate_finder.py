from candidate import CandidateFinder, Candidate
from feature import Feature
import re

MAX_LENGTH = 10000

class LabelCandidateFinder(CandidateFinder):

    def __init__(self, field, fid, max_xgap=MAX_LENGTH, max_ygap=MAX_LENGTH, bbox=None):
        """Set up parameters for the candidate search.

        :param field: The field to find.
        :param fid: The finder id of this object.
        :param max_xgap: The largest horizontal gap between label and candidate.
        :param max_ygap: The largest vertical gap between label and candidate.
        :param bbox: The bounding box in which to search.
        :return:
        """
        self._max_xgap = max_xgap
        self._max_ygap = max_ygap
        self._counts = {}
        self._bbox = bbox if bbox else [0, 0, MAX_LENGTH, MAX_LENGTH]
        CandidateFinder.__init__(self, field, fid)

    def _match_labels(self, document):
        """Find lines containing field labels.

        :param document: A Document object.
        :return: Generator of 2-tuples of lines and (start, end) of the match.
        """
        labels = self.field.labels
        pattern = self.field.settings.pattern_builder.list_pattern(labels)
        bbox = self._bbox

        for line in document.get_lines():
            if (bbox[0] <= line.x0 and line.x1 <= bbox[2] and
                    bbox[1] <= line.y0 and line.y1 <= bbox[3]):
                match = re.search(pattern, line.text)
                if match:
                    yield (line, match.span(0))


    def _find_next_lines(self, line):
        "Find lines following the given one, either vertically or horizontally"
        next_hor, next_vert = None, None

        candidates = [candidate for candidate in line.document.get_lines()
                      if candidate.page == line.page]
        ymin = line.y0 - self._max_ygap
        xmax = line.x1 + self._max_xgap
        for cand in candidates:
            # TODO account for possible page slant
            # Check for horizontal overlap
            if (cand.x1 >= line.x0 and cand.x0 <= line.x1 and
                ymin < cand.y1 < line.y0):
                try:
                    if cand.y0 > next_vert.y0:
                        next_vert = cand
                except AttributeError:
                    next_vert = cand
            # Check for vertical overlap
            elif ((cand.y0 <= 0.25 * line.y0 + 0.75 * line.y1 <= cand.y1 or
                   cand.y0 <= 0.75 * line.y0 + 0.25 * line.y1 <= cand.y1) and
                  line.x1 < cand.x0 < xmax):
                try:
                    if cand.x0 < next_hor.x0:
                        next_hor = cand
                except AttributeError:
                    next_hor = cand

        return next_hor, next_vert

    def get_candidates(self, document):
        """ Get candidates for a document.

        :param document: A Document object.
        :return: A list of LabelCandidates.
        """
        if not hasattr(document, "id"):
            document.id = 0
        self._counts[document.id] = 0

        strip_labels = self.field.settings.strip_labels
        results = [r for r in self._match_labels(document)]
        candidates = []
        field = self.field

        for line, span in results:
            next_horizontal, next_vertical = self._find_next_lines(line)
            line_continuation = next_horizontal.text if next_horizontal else ""

            # if there is no alphanumeric (TODO: allow configuration)
            #  here, consider next horizontal line
            h_text, h_line = (line.text[span[1]:], line) if re.search(r"[a-zA-Z0-9]", line.text[span[1]:]) \
                else (line_continuation, next_horizontal)
            h_text = strip_labels(h_text)
            v_text = strip_labels(next_vertical.text) if next_vertical else ""
            h_pre = [field.preprocess(text) for text in h_text]
            v_pre = [field.preprocess(text) for text in v_text]
            h_match = [field.find_value(text) for text in h_pre]
            v_match = [field.find_value(text) for text in v_pre]


            for match in h_match:
                if match and len(match):
                    try:
                        candidates.append(LabelCandidate(h_line, field, match, self.fid, self._counts[document.id], line))
                        self._counts[document.id] += 1
                        # shouldn't have more than one horizontal match
                        break
                    except Exception as e:
                        pass

            for match in v_match:
                if match and len(match):
                    try:
                        candidates.append(LabelCandidate(next_vertical, field, match, self.fid, self._counts[document.id], line))
                        self._counts[document.id] += 1
                    except Exception:
                        pass
        return candidates

class LabelCandidate(Candidate):
    """A class of Candidates storing information specific to labeled fields."""
    def __init__(self, line, field, match, generator_id, num, label_line):
        """Store the label line and call parent constructor."""
        self.label_line = label_line
        Candidate.__init__(self, line, field, match, generator_id, num)

class LabelOffsetX(Feature):
    """The horizontal offset between a candidate's line and its label.

    This is approximate since we don't store character positions in the database.
    We just go with the distance between left sides.
    """
    def compute(self, candidates):
        offsets = {}
        for candidate in candidates:
            if isinstance(candidate, LabelCandidate):
                offsets[candidate.id] = candidate.label_line.x0 - candidate.line.x0
            else:
                # For non-label candidates, choose a unique value.
                offsets[candidate.id] = - MAX_LENGTH
        return offsets

class LabelOffsetY(Feature):
    """The vertical offset between a candidate's line and its label.

    This is approximate since we don't store character positions in the database.
    We just go with the distance between bottoms.
    """
    def compute(self, candidates):
        offsets = {}
        for candidate in candidates:
            if isinstance(candidate, LabelCandidate):
                offsets[candidate.id] = candidate.label_line.y0 - candidate.line.y0
            else:
                offsets[candidate.id] = - MAX_LENGTH
        return offsets