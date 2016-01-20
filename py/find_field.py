from re import search


def build_character_pattern(character, substitutions):
    strings = [str(c) for c in (substitutions + [character])]
    return "(?:" + "|".join([s if len(s)== 1 else "(?:" + s + ")"
                     for s in strings]) + ")"


def build_label_pattern(label, substitutions):
    return "".join([c if c not in substitutions
                    else build_character_pattern(c, substitutions[c])
                    for c in label])


def build_field_pattern(field, substitutions):
    labels = field['labels'] + [label.upper() for label in field['labels']]
    return "|".join(["(?:" + build_label_pattern(label, substitutions) + ")"
                     for label in labels])


def find_field_label(field, document, page, substitutions):
    pattern = build_field_pattern(field, substitutions)
    lines = [line for line in document.lines if line.page == page]

    for line in lines:
        match = search(pattern, line.text)
        if match:
            yield (line, match.span(0))


def find_next_lines(line):
    "Find lines following the given one, either vertically or horizontally"
    next_horizontal, next_vertical = None, None
    candidates = [candidate for candidate in line.document.lines
                  if candidate.page==line.page and candidate.id != line.id]
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
        elif (candidate.y1 >= line.y0 and candidate.y0 <= line.y1 and
              candidate.x0 > line.x0):
            try:
                if candidate.x0 < next_horizontal.x0:
                    next_horizontal = candidate
            except AttributeError:
                next_horizontal = candidate

    return next_horizontal, next_vertical


def suggest_field_by_label(field, document, page, substitutions, all_fields):
    for line, span in find_field_label(field, document, page, substitutions):
        next_horizontal, next_vertical = find_next_lines(line)
        line_continuation = next_horizontal.text if next_horizontal else ""
        h_text = " ".join([line.text[span[1]:], line_continuation])
        h_text = strip_labels(h_text, all_fields, substitutions)
        v_text = strip_labels(next_vertical.text, all_fields, substitutions) if next_vertical else ""
        for pattern in field['patterns']:
            h_match = search(pattern, h_text)
            if h_match:
                yield h_match.group(0).strip()
            v_match = search(pattern, v_text)
            if v_match:
                yield v_match.group(0).strip()


def strip_labels(text, all_fields, substitutions):
    for field in all_fields:
        pattern = build_field_pattern(all_fields[field], substitutions)
        try:
            start = search(pattern, text).start(0)
            text = text[:start]
        except AttributeError:
            # search returned None
            pass
    return text


def get_field_value_by_label(field, document, page, substitutions, all_fields):
    "Get all suggestions for a field, and choose a single one"
    # TODO: find a way to reconcile different suggestions. for now, just return the first one
    for suggestion in suggest_field_by_label(field, document, page,
                                             substitutions, all_fields):
        return suggestion

    return None