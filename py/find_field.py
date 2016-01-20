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
    lines = [line for line in document.lines if line.page==page]
    result = []
    for line in lines:
        if search(pattern, line.text):
            result.append(line)
            # include positional information!

    return result
