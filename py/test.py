from settings import Settings
from sqlalchemy.orm import joinedload
import pandas as pd
import pickle
import yaml
import os
from argparse import ArgumentParser
from pdf_classes import *

if __name__ == "__main__":
    parser = ArgumentParser(description='Evaluate a model on the test set')
    parser.add_argument('model_file', help='the model definition YAML file',
                        default=None)
    parser.add_argument('--settings', help='the path to the settings file',
                        default=None)
    parser.add_argument('--token', help='a token for exported data',
                        default=None)
    args = parser.parse_args()

    settings = Settings(args.settings)

    with open(os.path.join(settings.get_directory('model'), args.model_file)) as f:
        model_def = yaml.load(f)

    field_name = model_def['field']
    field = settings.fields[field_name]

    with open(os.path.join(settings.get_directory('pickle'),
                           '%s.pkl' % args.model_file), 'r') as f:
        wrapper = pickle.load(f)

    y = []
    X = []

    settings.map_tables()
    session = settings.session()
    token = args.token

    #Attempt to preload candidate data from CSV files.
    if token:
        csv_dir = settings.get_directory('csv')
        features = pd.read_csv(os.path.join(csv_dir, '%s_test_features.%s.csv'
                                            % (field_name, token)), index_col=range(3))
        scores = pd.read_csv(os.path.join(csv_dir, '%s_test_scores.%s.csv'
                                          % (field_name, token)), index_col=range(3))['%s_score'%field_name]
        values = pd.read_csv(os.path.join(csv_dir, '%s_test_value.%s.csv'
                                          % (field_name, token)), index_col=range(3))['%s_value'%field_name]


    for document in session.query(Document).options(joinedload(Document.lines))\
            .filter(Document.is_test == 1):
        y.append(getattr(document, field_name))
        # Delete the field value from X to prevent cheating.
        delattr(document, field_name)
        X.append(document)

        if token:
            try:
                document.features = {field_name: features.xs(document.id, level='document', drop_level=False)}
                document.scores = {field_name: scores.xs(document.id, level='document', drop_level=False)}
                document.values = {field_name: values.xs(document.id, level='document', drop_level=False)}
            except KeyError as e:
                #Nothing found, but set them to empty to avoid trying to compute again later.
                document.features = {field_name: []}
                document.scores = {field_name: []}
                document.values = {field_name: []}

    print(wrapper.score(X, y))

