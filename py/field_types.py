import re
from sqlalchemy import String, Date
from dateutil.parser import parse
from datetime import date
from fuzzywuzzy import fuzz

from field import Field


class DateField(Field):
    patterns = [r"[\dIloO]{1,2}[/1Il-][\dIloO]{1,2}[/1Il-][\dIloO]{4}",
                 r"[\dIloO]{4}-[\dIloO]{2}-[\dIloO]{2}",
                 r"[\dIloO]{1,2}[/Il1-][\dIloO]{1,2}[/Il1-][\dIloO]{2}\b",
                 r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[\d]{1,2}\s*\d{4}"
                 ]
    col_type = Date

    def __init__(self, settings, name, data, allowed_range=None):
        self.start = None
        self.end = None
        if range is not None:
            self.start, self.end = allowed_range

        Field.__init__(self, settings, name, data)

    def get_value(self, text):
        replacements = [[(r"([0oIl1]?[\doOIl])[/I1l-]([oIl0123]?[\doOIl])[/I1l-]([\doOIl]{4})", r"\1/\2/\3"),
                         (r"[Il]", "1"), (r"[oO]", "0"), (r"^1([3-9])", "\1")],
                        [(r"[Il]", "1"), (r"[oO]", "0")],
                        [(r"([0oIl1]?[\doOIl])[/Il1-]([0oIl123]?[\doOIl])[/Il1-]([\doOIl]{2})", r"\1/\2/\3"),
                         (r"[Il]", "1"), (r"[oO]", "0"), (r"^1([3-9])", "\1")],
                        [(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*([0123]?[\d])\s*(\d{2,4})",
                          r"\1 \2, \3")]
                        ]
        for p, r in zip(self.patterns(), replacements):
            result = re.search(p, text)
            if result:
                new_text = result.group(0)
                for error, correction in r:
                    new_value = re.sub(error, correction, new_text)
                d = parse(new_text).date()
                # TODO: leave option for future years

                if d > self.end:
                    d = date(year=d.year-100, month=d.month, day=d.day)
                return d

    def preprocess(self, text):
        # Get rid of extra spacing
        if not re.search(r"[A-Z][a-z]{2}", text):
            text = re.sub(r"\s+", "", text)
        # Get rid of punctuation noise from scanning
        return str(text).translate(None, r",.'`")


class HumanNameField(Field):
    col_type = String(255)
    patterns = [r"[A-Za-z01\-\s,'.]+"]

    def get_value(self, text):
        #Get rid of extra spaces
        text = re.sub(r'\s+', ' ', text)
        #See if it's "Lastname, Firstname"
        result = re.search(r"([A-Za-z01\-\s']+)[,.]\s*([A-Za-z01\-\s']+.)", value)
        try:
            name = "%s %s" % (result.group(2), result.group(1))
        except AttributeError:
            # Maybe it's a name in "Firstname Lastname" format
            name = value
        #Maintain case unless it's all-caps
        if name.isupper():
            return name.title()
        else:
            return name


    def compare(self, value1, value2):
        try:
            return fuzz.ratio(value1, value2) / 100.
        except TypeError:
            return 0