from re import match
from sqlalchemy import Integer, String, Float, Boolean, Date
from datetime import date

# TODO: make everything in this file less awkward!!!!
def col_type(field):
    if field['type'] == 'human_name':
        return String(255)
    elif field['type'] == 'proper_noun':
        return String(1023)
    elif field['type'] == 'date':
        return Date


def post_process(field, value):
    if field['type'] == 'date':
        result = match(r'([01]?\d)[/1-]([0-3]?\d)[/1-](\d{4})', value)
        try:
            return date(int(result.group(3)), int(result.group(1)), int(result.group(2)))
        except ValueError:
            return None
    elif field['type'] == 'human_name':
        result = match(r'([A-Za-z01\-\s]+),\s*([A-Za-z01\-\s]+)', value)
        try:
            name = "%s %s" % (result.group(2), result.group(1))
            return name.title()
        except AttributeError:
            return value.title()
    elif field['type'] == 'proper_noun':
        return value.title()
