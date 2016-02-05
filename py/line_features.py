from settings import Settings
from argparse import ArgumentParser
from pdf_classes import *
import pandas as pd
from sqlalchemy.orm import joinedload
from os import path
import field_types



if __name__ == '__main__':
    parser = ArgumentParser(description='Compute features for lines')
    parser.add_argument('--settings', help='the path to the settings file',
                        default=None)
    parser.add_argument('--fields', help='the fields to generate data for',
                        nargs='*', default=None)

    args = parser.parse_args()
    settings = Settings(args.settings)
    settings.map_tables()
    session = settings.session()
    csv_directory = settings.get_directory('csv')

    fields = settings.fields()
    if args.fields is not None:
        fields = {name: field for name, field in fields.iteritems() if field_name in args.fields}

    candidates = {field_name: [] for field_name in fields}
    for document in session.query(Document).options(joinedload(Document.lines))\
            .filter(Document.is_test == 0):
        for field_name, field in fields.iteritems():
            if getattr(document, field_name) is None:
                continue
            doc_candidates = field.get_candidates(document)
            candidates[field_name].append(doc_candidates)

    for field_name, field in fields.iteritems():

        if "model_file" not in field:
            continue

        features = field.features_dataframe(candidates[field_name], field_name)
        features.to_csv(path.join(csv_directory, '%s_training_features.csv' % field_name), encoding='utf-8')

        col_name = "%s_score" % field_name
        handler = field_types.get_handler(field['type'])
        scores = {}
        all_candidates = sum(candidates[field_name], [])
        for candidate in all_candidates:
            value = getattr(candidate.line.document, field_name)
            row_key = candidate.id()
            scores[row_key] = handler.compare(value, candidate.formatted)


        score_df = pd.DataFrame({col_name: scores}).sort_index()
        score_df.index.names = ['page', 'line', 'hint_line', 'num', 'hint_order']
        score_df.to_csv(path.join(csv_directory, '%s_training_scores.csv' % field_name), encoding='utf-8')

        col_name = "%s_formatted" % field_name
        handler = field_types.get_handler(field['type'])
        texts = {}
        all_candidates = sum(candidates[field_name], [])
        for candidate in all_candidates:
            row_key = candidate.id()
            texts[row_key] = candidate.formatted

        text_df = pd.DataFrame({col_name: texts}).sort_index()
        text_df.index.names = ['page', 'line', 'hint_line', 'num', 'hint_order']
        text_df.to_csv(path.join(csv_directory, '%s_training_formatted.csv' % field_name), encoding='utf-8')
