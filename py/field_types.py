from re import match
from sqlalchemy import Integer, String, Float, Boolean, Date

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
        return "%s/%s/%s" % (result.group(3), result.group(1), result.group(2))
    elif field['type'] == 'human_name':
        result = match('([A-Za-z01\-\s]+),\s+([A-Za-z01\-\s]+)', value)
        name = "%s %s" % (result.group(2), result.group(1))
        return name.title()
    elif field['type'] == 'proper_noun':
        return value.title()