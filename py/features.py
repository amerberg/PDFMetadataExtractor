from feature import Feature
import re
import bisect

class LowerLeftX(Feature):
    """The x-coordinate of the lower left corner of the cadnidate's line."""
    def compute(self, candidates):
        return {candidate.id: candidate.line.x0 for candidate in candidates}


class LowerLeftY(Feature):
    """The y-coordinate of the lower left corner of the candidate's line."""
    def compute(self, candidates):
        return {candidate.id: candidate.line.y0 for candidate in candidates}


class CharsInString(Feature):
    """The number of characters from a specified string."""
    def __init__(self, field, string):
        self._string = string
        Feature.__init__(self, field)

    def compute(self, candidates):
        return {candidate.id: sum([candidate.value.count(c) for c in self._string]) for candidate in candidates}


class WordCount(Feature):
    """The number of words in a formatted candidate."""
    def compute(self, candidates):
        return {candidate.id: len(candidate.value.split()) for candidate in candidates}


class LineHeight(Feature):
    """The height of the line in which the candidate text is found."""
    def compute(self, candidates):
        return {candidate.id: candidate.line.y1 - candidate.line.y0 for candidate in candidates}


class XBox(Feature):
    """The x position of the candidate line relative to its containing box."""
    def compute(self, candidates):
        return {candidate.id: candidate.line.box.x0 - candidate.line.x0 for candidate in candidates}


class YBox(Feature):
    """The y position of the candidate line relative to its containing box."""
    def compute(self, candidates):
        return {candidate.id: candidate.line.y1 - candidate.line.box.y1 for candidate in candidates}


class PageNum(Feature):
    """The page on which a candidate is found."""
    def compute(self, candidates):
        return {candidate.id: candidate.line.page for candidate in candidates}


class AllCapsWordCount(Feature):
    """The number of words in a candidate match text."""
    def compute(self, candidates):
        return {candidate.id: len([w for w in candidate.match.split() if w.isupper()]) for candidate in candidates}


class InitCapsWordCount(Feature):
    """The number of words in the match value having only the first letter capitalized."""
    def compute(self, candidates):
        return {candidate.id: len([w for w in candidate.match.split()
                                     if w[0].isupper() and w[1:].islower()])
                for candidate in candidates}


class InitLowerWordCount(Feature):
    """The number of words in the match value having all letters lowercase."""
    def compute(self, candidates):
        return {candidate.id: len([w for w in candidate.match.split() if w.islower()]) for candidate in candidates}


class BoxRank(Feature):
    """The number of boxes above a given line's box on the page."""
    def compute(self, candidates):
        return {candidate.id: len([b for b in candidate.line.document.get_boxes()
                                   if b.y1 > candidate.line.box.y1 and
                                   b.page == candidate.line.page])
                for candidate in candidates}


class DictWordCount(Feature):
    """The number of dictionary words in a formatted candidate"""
    def __init__(self, field, word_file):
        """ Get the word list from the specified file.

        :param field: The field to which this feature belongs.
        :param word_file: The path to an alphabetized word list, one per line.
        :return: None
        """
        word_file = field.settings.resolve_path(word_file)
        with open(word_file, 'r') as f:
            words = f.readlines()
        words = [w.strip() for w in words if w.islower()]
        self._dict_words = words
        Feature.__init__(self, field)

    def _is_dict_word(self, word):
        word = word.lower()
        dict_words = self._dict_words
        ind = bisect.bisect_left(dict_words, word)
        if ind != len(dict_words) and dict_words[ind] == word:
            return True
        return False

    def compute(self, candidates):
        result = {}
        for candidate in candidates:
            line_words = [w.strip("\"';.:.!?") for w in candidate.value.split()]
            result[candidate.id] = len([w for w in line_words if self._is_dict_word(w.lower())])
        return result


class BoxPhrases(Feature):
    """The number of matches for a list of phrases in a candidates's box."""
    def __init__(self, field, phrases):
        self._phrases = phrases
        Feature.__init__(self, field)

    def compute(self, candidates):
        result = {candidate.id: {} for candidate in candidates}
        pb = self.field.settings.pattern_builder
        for candidate in candidates:
            pattern = pb.list_pattern(self._phrases)

            result[candidate.id] = len([1 for line in candidate.line.box.get_lines()
                                         if re.search(pattern, line.text) is not None])

        return result


class ContainsString(Feature):
    """Whether a candidate's line contains a given string."""
    def __init__(self, field, string):
        self._string = string
        Feature.__init__(self, field)

    def compute(self, candidates):
        return {candidate.id: int(self._string in candidate.line.text) for candidate in candidates}


class Length(Feature):
    """The length of a candidate value."""
    def compute(self, candidates):
        return {candidate.id: len(candidate.value) for candidate in candidates}


class DigitCount(Feature):
    """The number of digits in a candidate's value."""
    def compute(self, candidates):
        return {candidate.id: sum([c.isdigit() for c in candidate.value]) for candidate in candidates}


class AlphaCount(Feature):
    """The number of alphabetic characters in a candidate's value."""
    def compute(self, candidates):
        return {candidate.id: sum([c.isalpha() for c in candidate.value]) for candidate in candidates}


class RankValue(Feature):
    """The candidate's rank among all values for a document."""

    def __init__(self, field, reverse=False):
        self.reverse = reverse
        Feature.__init__(self, field)

    def compute(self, candidates):
        values = sorted(list({c.value for c in candidates}), reverse=self.reverse)
        return {c.id: values.index(c.value) for c in candidates}


class FinderId(Feature):
    """The identifier for the CandidateFinder that found a candidate."""
    def compute(self, candidates):
        return {candidate.id: candidate.finder_id() for candidate in candidates}
