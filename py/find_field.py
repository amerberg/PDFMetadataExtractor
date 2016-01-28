from re import search
from field_types import get_handler

import q

class PatternBuilder(object):
    def __init__(self, substitutions):
        self._substitutions = substitutions
        self._char_patterns = {}
        self._label_patterns = {}
        self._field_patterns = {}

    def character_pattern(self, character):
        try:
            return self._char_patterns[character]
        except KeyError:
            substitutions = self._substitutions[character]
            strings = [str(c) for c in (substitutions + [character])]
            self._char_patterns[character] = "(?:" + "|".join(
                [s if len(s) == 1 else "(?:" + s + ")" for s in strings]) + ")"
            return self._char_patterns[character]

    def label_pattern(self, label):
        try:
            return self._label_patterns[label]
        except KeyError:
            substitutions = self._substitutions
            self._label_patterns[label] = "\s*".join([c if c not in substitutions
                    else self.character_pattern(c)
                    for c in label])
            return self._label_patterns[label]

    def field_pattern(self, field):

        if 'labels' not in field:
            return None

        try:
            key = "$".join(field['labels'])
            return self._field_patterns[key]
        except KeyError:
            labels = field['labels'] + [label for label in field['labels']]
            self._field_patterns[key] = "|".join(["(?:" + self.label_pattern(label) + ")"
                for label in labels])
            return self._field_patterns[key]


def find_field_label(field, document, page, pattern_builder):
    pattern = pattern_builder.field_pattern(field)

    for line in document.lines:
        if line.page == page:
            match = search(pattern, line.text)
            if match:
                yield (line, match.span(0))


def find_next_lines(line):
    "Find lines following the given one, either vertically or horizontally"
    next_horizontal, next_vertical = None, None
    candidates = [candidate for candidate in line.document.lines
                  if candidate.page == line.page]
    for candidate in candidates:
        # TODO account for possible page slant
        # Check for horizontal overlap
        if (candidate.x1 >= line.x0 and candidate.x0 <= line.x1 and
                candidate.y0 < line.y0):
            try:
                if candidate.y0 < next_vertical.y0:
                    next_vertical = candidate
            except AttributeError:
                if candidate.y0 < line.y0:
                    next_vertical = candidate
        # Check for vertical overlap
        elif ((candidate.y0 <= 0.25*line.y0+0.75*line.y1 <= candidate.y1 or
              candidate.y0 <= 0.75*line.y0+0.25*line.y1 <= candidate.y1) and
              candidate.x0 > line.x0):
            try:
                if candidate.x0 < next_horizontal.x0:
                    next_horizontal = candidate
            except AttributeError:
                next_horizontal = candidate

    return next_horizontal, next_vertical


def suggest_field_by_label(field, document, page, pattern_builder, all_fields):
    results = [r for r in find_field_label(field, document, page, pattern_builder)]
    results.sort(key=lambda x: x[1][0]-x[1][1])
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

        for match in h_match:
            if match:
                yield (match, h_line)
        for match in v_match:
            if match:
                yield (match, next_vertical)

def strip_labels(text, all_fields, pattern_builder):
    for field in all_fields:
        pattern = pattern_builder.field_pattern(all_fields[field])
        if pattern is None:
            continue
        try:
            # TODO: consider possibility of multiple matches...
            match = search(pattern, text)
            # TODO: do something less clumsy than joining on newlines...
            text = "\n".join([text[:match.start(0)], text[match.end(0)]])
        except AttributeError:
            # search returned None
            pass
    return text.split("\n")


def get_field_value_by_label(field, document, page, pattern_builder, all_fields):
    "Get all suggestions for a field, and choose a single one"
    # TODO: find a way to reconcile different suggestions. for now, just return the first one
    for suggestion, _ in suggest_field_by_label(field, document, page,
                                             pattern_builder, all_fields):
        return suggestion

    return None
