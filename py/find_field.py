from re import search
from field_types import get_handler
import uuid


class PatternBuilder(object):
    def __init__(self, substitutions):
        self._substitutions = substitutions
        self._char_patterns = {}
        self._string_patterns = {}
        self._list_patterns = {}

    def character_pattern(self, character):
        try:
            return self._char_patterns[character]
        except KeyError:
            substitutions = self._substitutions[character]
            strings = [str(c) for c in (substitutions + [character])]
            self._char_patterns[character] = "(?:" + "|".join(
                [s if len(s) == 1 else "(?:" + s + ")" for s in strings]) + ")"
            return self._char_patterns[character]

    def string_pattern(self, string):
        try:
            return self._string_patterns[string]
        except KeyError:
            substitutions = self._substitutions
            self._string_patterns[string] = "\s*".join([c if c not in substitutions
                    else self.character_pattern(c)
                    for c in string])
            return self._string_patterns[string]

    def list_pattern(self, strings):
        try:
            key = "$".join(strings)
            return self._list_patterns[key]
        except KeyError:
            strings = set(strings + [string.upper() for string in strings])
            self._list_patterns[key] = "|".join(["(?:" + self.string_pattern(string) + ")"
                for string in strings])
            return self._list_patterns[key]


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
        return "c_%s_%s_%d_%d" % (str(self._line_id(self.line)),
                                  str(self._line_id(self.hint_line)),
                                  num, self.hint_order)

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



def match_list(strings, document, pattern_builder):
    pattern = pattern_builder.list_pattern(strings)

    for line in document.lines:
        match = search(pattern, line.text)
        if match:
            yield (line, match.span(0))


def find_next_lines(line):
    "Find lines following the given one, either vertically or horizontally"
    next_hor, next_vert = None, None

    candidates = [candidate for candidate in line.document.lines
                  if candidate.page == line.page]
    for cand in candidates:
        # TODO account for possible page slant
        # Check for horizontal overlap
        if (cand.x1 >= line.x0 and cand.x0 <=line.x1 and
                cand.y0 < line.y0):
            try:
                if cand.y0 > next_vert.y0:
                    next_vert = cand
            except AttributeError:
                next_vert = cand
        # Check for vertical overlap
        elif ((cand.y0 <= 0.25*line.y0+0.75*line.y1 <= cand.y1 or
              cand.y0 <= 0.75*line.y0+0.25*line.y1 <= cand.y1) and
              cand.x0 > line.x0):
            try:
                if cand.x0 < next_hor.x0:
                    next_hor = cand
            except AttributeError:
                next_hor = cand

    return next_hor, next_vert

def find_prev_lines(line):
    "Find lines following the given one, either vertically or horizontally"
    # TODO: merge this with find_next lines, perhaps in the context of a general
    #       framework for simple constrained optimization
    prev_hor, prev_vert = None, None

    candidates = [candidate for candidate in line.document.lines
                  if candidate.page == line.page]
    for cand in candidates:
        # TODO account for possible page slant
        # Check for horizontal overlap
        if (cand.x1 >= line.x0 and cand.x0 <= line.x0 and
                cand.y0 > line.y0):
            try:
                if cand.y0 < prev_vert.y0:
                    prev_vert = cand
            except AttributeError:
                    prev_vert = cand
        # Check for vertical overlap
        elif ((cand.y0 <= 0.25*line.y0+0.75*line.y1 <= cand.y1 or
              cand.y0 <= 0.75*line.y0+0.25*line.y1 <= cand.y1) and
              cand.x0 < line.x0):
            try:
                if cand.x0 > prev_hor.x0:
                    prev_hor = cand
            except AttributeError:
                prev_hor = cand

    return prev_hor, prev_vert

def suggest_field_by_label(field, document, pattern_builder, all_fields):
    results = [r for r in match_list(field['labels'], document, pattern_builder)]
    results.sort(key=lambda x: x[1][0]-x[1][1])
    candidates = []

    for line, span in results:
        next_horizontal, next_vertical = find_next_lines(line)
        line_continuation = next_horizontal.text if next_horizontal else ""

        # if there is no alphanumeric (TODO: allow configuration)
        #  here, consider next horizontal line
        h_text, h_line = (line.text[span[1]:], line) if search(r"[a-zA-Z0-9]", line.text[span[1]:]) \
            else (line_continuation, next_horizontal)
        h_text = strip_labels(h_text, all_fields, pattern_builder)
        v_text = strip_labels(next_vertical.text, all_fields, pattern_builder) if next_vertical else ""
        handler = get_handler(field['type'])
        h_pre = [handler.preprocess(text) for text in h_text]
        v_pre = [handler.preprocess(text) for text in v_text]
        h_match = [handler.find_value(text) for text in h_pre]
        v_match = [handler.find_value(text) for text in v_pre]

        for num, match in enumerate(h_match):
            if match and len(match):
                try:
                    candidates.append(Candidate(h_line, field, match, line, 1, num))
                except:
                    pass

        for num, match in enumerate(v_match):
            if match and len(match):
                try:
                    candidates.append(Candidate(next_vertical, field, match, line, 1, num))
                except Exception:
                    pass
    return candidates

def suggest_field_by_after_text(field, document, pattern_builder, all_fields):
    try:
        results = [r for r in match_list(field['after_text'], document, pattern_builder)]
    except KeyError:
        return []

    results.sort(key=lambda x: x[1][0]-x[1][1])
    candidates = []

    for line, span in results:
        prev_horizontal, prev_vertical = find_prev_lines(line)
        line_start = prev_horizontal.text if prev_horizontal else ""

        # if there is no alphanumeric (TODO: allow configuration)
        #  here, consider next horizontal line
        h_text, h_line = (line.text[:span[0]], line) if search(r"[a-zA-Z0-9]", line.text[:span[0]]) \
            else (line_start, prev_horizontal)
        h_text = strip_labels(h_text, all_fields, pattern_builder)
        v_text = strip_labels(prev_vertical.text, all_fields, pattern_builder) if prev_vertical else ""
        handler = get_handler(field['type'])
        h_pre = [handler.preprocess(text) for text in h_text]
        v_pre = [handler.preprocess(text) for text in v_text]
        h_match = [handler.find_value(text) for text in h_pre]
        v_match = [handler.find_value(text) for text in v_pre]

        for num, match in enumerate(h_match):
            if match and len(match):
                try:
                    candidates.append(Candidate(h_line, field, match, line, -1, num))
                except:
                    pass

        for num, match in enumerate(v_match):
            if match and len(match):
                try:
                    candidates.append(Candidate(prev_vertical, field, match, line, -1, num))
                except:
                    pass

    return candidates

def suggest_field(field, document, pattern_builder, all_fields):
    return suggest_field_by_label(field, document, pattern_builder, all_fields)\
        + suggest_field_by_after_text(field, document, pattern_builder, all_fields)

def strip_labels(text, all_fields, pattern_builder):
    for field_name, field in all_fields.iteritems():
        if "labels" not in field:
            continue
        pattern = pattern_builder.list_pattern(field['labels'])
        if pattern is None:
            continue
        try:
            # TODO: consider possibility of multiple matches...
            match = search(pattern, text)
            # TODO: do something less clumsy than joining on newlines...
            text = "\n".join([text[:match.start(0)], text[match.end(0):]])
        except AttributeError:
            # search returned None
            pass
    return text.split("\n")