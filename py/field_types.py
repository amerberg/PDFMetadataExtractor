import re
from sqlalchemy import Integer, String, Float, Boolean, Date
from dateutil.parser import parse
from datetime import date
from fuzzywuzzy import fuzz

def get_handler(type):
    classes = {'human_name' : HumanNameHandler,
               'date' : DateHandler,
               'proper_noun' : ProperNounHandler
               }
    return classes[type]()

class TypeHandler(object):
    def format(self, value):
        pass
    def patterns(self):
        return self._patterns
    def col_type(self):
        return self._col_type
    def format(self, value):
        return value
    def preprocess(self, text):
        return text
    def find_value(self, text):
        for pattern in self.patterns():
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None

    def compare(self, value1, value2):
        return value1 == value2


class HumanNameHandler(TypeHandler):
    _col_type = String(255)
    _patterns = [r"[A-Za-z01\-\s,'.]+"]

    def format(self, value):
        value = re.sub(r'\s+', ' ', value)
        result = re.search(r"([A-Za-z01\-\s']+),\s*([A-Za-z01\-\s']+.)", value)
        try:
            name = "%s %s" % (result.group(2), result.group(1))
        except AttributeError:
            # Maybe it's a name in "Firstname Lastname" format
            name = value

        if name.isupper():
            return name.title()
        else:
            return name

    def compare(self, value1, value2):
        return fuzz.ratio(value1, value2) / 100.


class DateHandler(TypeHandler):
    _patterns = [r"[\dIloO]{1,2}[/1Il-][\dIloO]{1,2}[/1Il-][\dIloO]{4}",
                 r"[\dIloO]{4}-[\dIloO]{2}-[\dIloO]{2}",
                 r"[\dIloO]{1,2}[/Il1-][\dIloO]{1,2}[/Il1-][\dIloO]{2}\b",
                 r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[\d]{1,2}\s*\d{4}"
                 ]
    _col_type = Date

    def format(self, value):
        replacements = [[(r"([0oIl1]?[\doOIl])[/I1l-]([oIl0123]?[\doOIl])[/I1l-]([\doOIl]{4})", r"\1/\2/\3"),
                         (r"[Il]", "1"), (r"[oO]", "0"), (r"^1([3-9])", "\1")],
                        [(r"[Il]", "1"), (r"[oO]", "0")],
                        [(r"([0oIl1]?[\doOIl])[/Il1-]([0oIl123]?[\doOIl])[/Il1-]([\doOIl]{2})", r"\1/\2/\3"),
                         (r"[Il]", "1"), (r"[oO]", "0"), (r"^1([3-9])", "\1")],
                        [(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*([0123]?[\d])\s*(\d{2,4})",
                          r"\1 \2, \3")]
                        ]
        for p, r in zip(self.patterns(), replacements):
            result = re.search(p, value)
            if result:
                new_value = result.group(0)
                for error, correction in r:
                    new_value = re.sub(error, correction, new_value)
                d = parse(new_value).date()
                # TODO: leave option for future years
                if d.year > date.today().year:
                    d = date(year=d.year-100, month=d.month, day=d.day)
                return d

    def preprocess(self, value):
        # Get rid of extra spacing
        if not re.search(r"[A-Z][a-z]{2}", value):
            value = re.sub(r"\s+", "", value)
        # Get rid of punctuation noise from scanning
        return str(value).translate(None, r",.'`")



class ProperNounHandler(TypeHandler):
    _col_type = String(1023)
    _patterns = [r".+"]

    def format(self, value):
        return value.title()
