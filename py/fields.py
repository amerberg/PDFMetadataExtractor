import re
from sqlalchemy import String, Date
from dateutil.parser import parse
from datetime import date
from fuzzywuzzy import fuzz
import bisect

from field import Field


class DateField(Field):
    """Field class for date fields"""
    patterns = [r"[\dIloO]{1,2}[/1Il-][\dIloO]{1,2}[/1Il-][\dIloO]{4}",
                 r"[\dIloO]{4}-[\dIloO]{2}-[\dIloO]{2}",
                 r"[\dIloO]{1,2}[/Il1-][\dIloO]{1,2}[/Il1-][\dIloO]{2}\b",
                 r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[\d]{1,2}\s*\d{4}"
                 ]
    col_type = Date

    def __init__(self, settings, name, data, allowed_range=None):
        """Set the allowed range if specified."""
        self.start = None
        self.end = None
        if allowed_range is not None:
            self.start, self.end = allowed_range

        Field.__init__(self, settings, name, data)


    def preprocess(self, text):
        """Get rid of extra spacing and punctuation."""
        if not re.search(r"[A-Z][a-z]{2}", text):
            text = re.sub(r"\s+", "", text)
        # Sometimes we get extra punctuation from scanner noise.
        preprocessed = str(text).translate(None, r",.'`")
        return preprocessed

    def get_value(self, text):
        """Match patterns, correct OCR substitutions, convert to date type.

        :param text: preprocessed candidate text
        :return: a date object corresponding to the given text.
        """

        replacements = [[(r"([0oIl1]?[\doOIl])[/I1l-]([oIl0123]?[\doOIl])[/I1l-]([\doOIl]{4})", r"\1/\2/\3"),
                         (r"[Il]", "1"), (r"[oO]", "0"), (r"^1([3-9])", "\1")],
                        [(r"[Il]", "1"), (r"[oO]", "0")],
                        [(r"([0oIl1]?[\doOIl])[/Il1-]([0oIl123]?[\doOIl])[/Il1-]([\doOIl]{2})", r"\1/\2/\3"),
                         (r"[Il]", "1"), (r"[oO]", "0"), (r"^1([3-9])", "\1")],
                        [(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*([0123]?[\d])\s*(\d{2,4})",
                          r"\1 \2, \3")]
                        ]
        for p, r in zip(self.patterns, replacements):
            result = re.search(p, text)
            if result:
                new_text = result.group(0)
                for error, correction in r:
                    new_text = re.sub(error, correction, new_text)
                d = parse(new_text).date()

                #TODO: this isn't the right solution in general, but it does what I need now
                if self.end and d > self.end:
                    d = date(year=d.year-100, month=d.month, day=d.day)
                return d

    def compare(self, date1, date2):
        return str(date1) == str(date2)


class HumanNameField(Field):
    """ A field class for human names."""
    col_type = String(255)
    patterns = [r"[A-Za-z01\-\s,'.]+"]

    def __init__(self, settings, name, data, first_name_list=None):
        """Get a first name list if necessary and call parent constructor."""
        if first_name_list:
            first_name_list = settings.resolve_path(first_name_list)
            with open(first_name_list, 'r') as f:
                self._first_name_list = f.read().splitlines()
        else:
            self._first_name_list = []
        Field.__init__(self, settings, name, data)


    def get_value(self, text):
        """Normalize name to 'Firstname M Lastname' format."""
        #Get rid of extra spaces
        text = re.sub(r'\s+', ' ', text)
        #See if it's "Lastname, Firstname"
        result = re.search(r"([A-Za-z01\-\s']+)[,.]\s*([A-Za-z01\-\s']+.)", text)
        try:
            name = " ".join([result.group(2), result.group(1)])
        except AttributeError:
            name = ""
            #Maybe OCR missed a comma...
            words = text.split(" ")
            if len(words) == 3 and len(words[2].strip('.,')) == 1:
                #"Lastname Firstname M."
                name = " ".join([words[1], words[2], words[0]])
            elif len(words) == 2 and self._is_first_name(words[1]) and\
                    not self._is_first_name(words[0]):
                name = " ".join([words[1], words[0]])
            #If there were spaces between all the letters, collapse and try to separate.
            if max([len(w) for w in words]) == 1:
                words = ["".join(words)]
            if len(words) == 1:
                name = self._break_single_name(words[0])
            elif name == "":
                # Assume it's just a name in "Firstname Lastname" format
                name = text
        #Maintain case unless it's all-caps
        if name.isupper():
            return name.title()
        else:
            return name

    def _is_first_name(self, word):
        """Check whether a given word appears in the list of first names."""
        names = self._first_name_list
        word = word.lower()
        ind = bisect.bisect_left(names, word)
        if ind < len(names) and names[ind] == word:
            return True
        return False

    def _break_single_name(self, word):
        """Given a single word, try to break it into first and last names."""
        #First see if the beginning of word is in the name list.
        lower = word.lower()
        names = self._first_name_list
        ind = bisect.bisect_left(names, lower)
        if ind < len(names) and lower.startswith(names[ind]):
            length = len(names[ind])
            return word[:length] + " " + word[length:]
        #Now try the end of the string.
        max_valid = 0
        for length in range(2, len(word)):
            if self._is_first_name(word[-length:]):
                max_valid = length
        if max_valid > 0:
            return word[-max_valid:] + " " + word[:-max_valid]

        return word


    def compare(self, value1, value2):
        """Use the Levenshtein-based similarity measure."""
        try:
            return fuzz.ratio(value1, value2) / 100.
        except TypeError:
            return 0