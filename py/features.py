from feature import Feature
import re

class lower_left_x(Feature):
   def compute(self, candidates):
        return {candidate.id: candidate.line.x0 for candidate in candidates}

class lower_left_y(Feature):
    def compute(self, candidates):
        return {candidate.id: candidate.line.y0 for candidate in candidates}

class chars_in_string(Feature):
    def __init__(self, field, string):
        self._string = string
        Feature.__init__(self, field)

    def compute(self, candidates):
        return {candidate.id: sum([candidate.formatted.count(c) for c in self._string]) for candidate in candidates}

class word_count(Feature):
    def compute(self, candidates):
        return {candidate.id: len(candidate.formatted.split()) for candidate in candidates}

class line_height(Feature):
    def compute(self, candidates):
        return {candidate.id: candidate.line.y1 - candidate.line.y0 for candidate in candidates}

class x_box(Feature):
    def compute(self, candidates):
        return {candidate.id: candidate.line.box.x0 - candidate.line.x0 for candidate in candidates}

class y_box(Feature):
    def compute(self, candidates):
        return {candidate.id: candidate.line.y1 - candidate.line.box.y1 for candidate in candidates}

class page_num(Feature):
    def compute(self, candidates):
        return {candidate.id: candidate.line.page for candidate in candidates}

class all_caps_word_count(Feature):
    def compute(self, candidates):
        return {candidate.id: len([w for w in candidate.match.split() if w.isupper()]) for candidate in candidates}

class init_caps_word_count(Feature):
    def compute(self, candidates):
        return {candidate.id: len([w for w in candidate.match.split()
                                     if w[0].isupper() and w[1:].islower()])
                for candidate in candidates}

class init_lower_word_count(Feature):
    def compute(self, candidates):
        return {candidate.id: len([w for w in candidate.match.split() if w.islower()]) for candidate in candidates}

class box_rank(Feature):
    def compute(self, candidates):
        return {candidate.id: len([b for b in candidate.line.document.get_boxes() if b.y1 > candidate.line.box.y1
                    and b.page == candidate.line.page]) for candidate in candidates}

class dict_word_count(Feature):
    def __init__(self, field, word_file):
        with open(word_file, 'r') as f:
            words = f.readlines()
        words = [w.strip() for w in words if w.islower()]
        self._words = words
        Feature.__init__(self, field)

    def compute(self, candidates):
        result = {}
        for candidate in candidates:
            line_words = [w.strip("\"';.:.!?") for w in candidate.match.split()]
            result[candidate.id] = len([w for w in line_words if w.lower() in self._words])
        return result

class box_phrases(Feature):
    def __init__(self, field, phrases):
        self._phrases = phrases
        Feature.__init__(self, field)

    def compute(self, candidates):
        result = {candidate.id: {} for candidate in candidates}
        for candidate in candidates:
            pb = self.field.settings.pattern_builder
            pattern = pb.list_pattern(self._phrases)

            result[candidate.id] = len([1 for line in candidate.line.box.get_lines()
                                         if re.search(pattern, line.text) is not None])

        return result

class contains_string(Feature):
    def __init__(self, field, string):
        self._string = string
        Feature.__init__(self, field)

    def compute(self, candidates):
        return {candidate.id: int(self._string in candidate.line.text) for candidate in candidates}

class length(Feature):
    def compute(self, candidates):
        return {candidate.id: len(candidate.formatted) for candidate in candidates}

class digit_count(Feature):
    def compute(self, candidates):
        return {candidate.id: sum([c.isdigit() for c in candidate.formatted]) for candidate in candidates}

class alpha_count(Feature):
    def compute(self, candidates):
        return {candidate.id: sum([c.isalpha() for c in candidate.formatted]) for candidate in candidates}


class rank_value(Feature):
    def __init__(self, field, reverse=False):
        self.reverse = reverse
        Feature.__init__(self, field)

    def compute(self, candidates):
        values = sorted(list({c.value for c in candidates}), reverse=self.reverse)
        return {c.id: values.index(c.value) for c in candidates}
