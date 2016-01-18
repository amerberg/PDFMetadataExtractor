
def build_character_pattern(character, substitutions):
    substitutions.append(character)
    substitutions = [str(c) for c in substitutions]
    return "(?:" + "|".join([s if len(s)== 1 else "(?:" + s + ")"
                     for s in substitutions]) + ")"

def build_label_pattern(label, substitutions):
    return "".join([c if c not in substitutions
                    else build_character_pattern(c, substitutions[c])
                    for c in label])

def build_field_pattern(field, substitutions):
    return "|".join(["(?:" + build_label_pattern(label, substitutions) + ")"
                     for label in field['labels']])