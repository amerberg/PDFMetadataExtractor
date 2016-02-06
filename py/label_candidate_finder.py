from candidate import *
import re

class LabelCandidateFinder(CandidateFinder):

    def __init__(self, field, gid, pattern_builder, max_xgap=10000, max_ygap=10000, bbox=None):
        self._max_xgap = max_xgap
        self._max_ygap = max_ygap
        self._counts = {}
        self._bbox = bbox if bbox else [0, 0, 10000, 10000]
        CandidateFinder.__init__(self, field, gid, pattern_builder)

    def match_labels(self, document):
        labels = self.field.labels
        pattern = self._pattern_builder.list_pattern(labels)
        bbox = self._bbox

        for line in document.get_lines():
            if (bbox[0] <= line.x0 and line.x1 <= bbox[2] and bbox[1] <= line.y0 and line.y1 <= bbox[3]):
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
        if not hasattr(document, "id"):
            document.id = 0
        self._counts[document.id] = 0

        strip_labels = self.field.settings.strip_labels
        results = [r for r in self.match_labels(document)]
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
                        candidates.append(LabelCandidate(h_line, field, match, self.gid, self._counts[document.id], line))
                        self._counts[document.id] += 1
                        # shouldn't have more than one horizontal match
                        break
                    except Exception as e:
                        pass

            for match in v_match:
                if match and len(match):
                    try:
                        candidates.append(LabelCandidate(next_vertical, field, match, self.gid, self._counts[document.id], line))
                        self._counts[document.id] += 1
                    except Exception:
                        pass
        return candidates

class LabelCandidate(Candidate):
    def __init__(self, line, field, match, generator_id, num, label_line):
        self.label_line = label_line
        self.label_offset_x = label_line.x0 - line.x0
        self.label_offset_y = label_line.y0 - line.x0
        Candidate.__init__(self, line, field, match, generator_id, num)
