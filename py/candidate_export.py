"""Find candidates and export all information needed for training and prediction."""

from settings import Settings
from argparse import ArgumentParser
from pdf_classes import *
import pandas as pd
from sqlalchemy.orm import joinedload
from os import path
import uuid

if __name__ == '__main__':
    parser = ArgumentParser(description='Compute features for lines')
    parser.add_argument('--settings', help='the path to the settings file',
                        default=None)
    parser.add_argument('--fields', help='the fields to generate data for',
                        nargs='*', default=None)
    parser.add_argument('--test', help='flag indicating that test set should be used',
                        action='store_true', default=None)
    args = parser.parse_args()

    settings = Settings(args.settings)
    settings.map_tables()
    session = settings.session()
    csv_directory = settings.get_directory('csv')
    token = uuid.uuid1()

    dataset = "test" if args.test else "training"

    #If field names have been specified on the command line, only export those ones.
    fields = settings.fields
    if args.fields is not None:
        fields = {name: field for name, field in fields.iteritems() if name in args.fields}

    #Get all candidates for all fields.
    candidates = {field_name: [] for field_name in fields}
    for document in session.query(Document).options(joinedload(Document.lines))\
            .filter(Document.is_test == args.test):
        for field_name, field in fields.iteritems():
            if getattr(document, field_name) is None:
                continue
            doc_candidates = field.get_candidates(document)
            candidates[field_name].append(doc_candidates)

    #For each field, compute features, scores, and values for candidates.
    for field_name, field in fields.iteritems():
        features = field.features_dataframe(candidates[field_name])
        features.to_csv(path.join(csv_directory, '%s_%s_features.%s.csv'
                                  % (field_name, dataset, token)), encoding='utf-8')

        col_name = "%s_score" % field_name
        scores = {}
        all_candidates = sum(candidates[field_name], [])

        for candidate in all_candidates:
            value = getattr(candidate.line.document, field_name)
            row_key = candidate.id
            scores[row_key] = field.compare(value, candidate.value)

        score_df = pd.DataFrame({col_name: scores}).sort_index()
        score_df.index.names = features.index.names
        score_df.to_csv(path.join(csv_directory, '%s_%s_scores.%s.csv'
                                  % (field_name, dataset, token)), encoding='utf-8')

        col_name = "%s_value" % field_name
        texts = {}
        all_candidates = sum(candidates[field_name], [])
        for candidate in all_candidates:
            row_key = candidate.id
            texts[row_key] = candidate.value

        value_df = pd.DataFrame({col_name: texts}).sort_index()
        value_df.index.names = features.index.names
        value_df.to_csv(path.join(csv_directory, '%s_%s_value.%s.csv'
                                  % (field_name, dataset, token)), encoding='utf-8')

    print("Candidates exported. Token: %s" % token)
