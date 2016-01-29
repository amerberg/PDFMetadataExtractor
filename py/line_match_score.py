from settings import load_settings, default_settings_file, resolve_path
from argparse import ArgumentParser
from field_types import get_handler
from schema import *
import db
import pandas as pd
from sqlalchemy.orm import joinedload
from os import path
import time
from exceptions import ZeroDivisionError


if __name__ == '__main__':
    parser = ArgumentParser(description='Compute features for lines')
    parser.add_argument('--settings', help='the path to the settings file',
                           default=None)

    args = parser.parse_args()
    settings_file = args.settings if args.settings else default_settings_file()
    settings = load_settings(settings_file)
    csv_directory = resolve_path(settings['csv_directory'], settings_file)

    settings = load_settings()
    map_tables(settings['fields'])
    Session = db.session(settings)
    session = Session()


    all_fields = settings['fields'].copy()
    all_fields.update(settings['ignore_fields'])
    df = pd.DataFrame()

    series = {}

    for field_name in settings['fields']:
        field = settings['fields'][field_name]

        try:
            if field['disabled']:
                continue
        except KeyError:
            pass

        try:
            if not field['model']:
                continue
        except KeyError:
            continue

        handler = get_handler(field['type'])

        scores = {}
        sym_scores = {}
        col_name = field_name + "_score"
        query = session.query(Document).options(joinedload(Document.lines)).\
            filter(Document.is_test == 0)
        for document in query.all():
            value = getattr(document, field_name)
            row_key = 'line_%d' % line.id
            doc_scores = {row_key:
                        handler.match_score(value, line.text) for line in document.get_lines()}
            doc_sym_scores = {row_key:
                        handler.compare(value, line.text) for line in document.get_lines()}
            scores.update(doc_scores)
            sym_scores.update(doc_sym_scores)


    df = pd.DataFrame({col_name: scores, 'sym_' + col_name: sym_scores})
    df.to_csv(path.join(csv_directory, 'training_scores.csv'), encoding='utf-8')
