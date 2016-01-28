from settings import load_settings, resolve_path, default_settings_file
from find_field import suggest_field_by_label, PatternBuilder
from argparse import ArgumentParser
from schema import *
import db
import pandas as pd
import numpy as np
from sqlalchemy.orm import joinedload
from os import path

class FeatureBuilder(object):

    def __init__(self, fields, dictionary, features=None, box_phrases={}, pattern_builder=None):
        self._feature_names = set(sum([fields[f]["features"] for f in fields
                                 if "features" in fields[f]], [])) if not features else features
        self._dict = dictionary
        self._box_phrases = box_phrases
        self._pattern_builder = pattern_builder
        self._next_temp_id = 1



    def _feature_func(self, name):
        funcs = {'lower_left_x': self.lower_left_x,
                 'lower_left_y': self.lower_left_y,
                 'space_count': self.space_count,
                 'punctuation_count': self.punctuation_count,
                 'word_count': self.word_count,
                 'line_height':  self.line_height,
                 'x_box': self.x_box,
                 'y_box': self.y_box,
                 'page_num': self.page_num,
                 'all_caps_word_count': self.all_caps_word_count,
                 'init_caps_word_count': self.init_caps_word_count,
                 'init_lower_word_count': self.init_lower_word_count,
                 'box_rank': self.box_rank,
                 'dict_word_count': self.dict_word_count,
                 'box_phrases': self.box_phrases,
                 'contains_colon': self.contains_colon}
        return funcs[name]

    def line_features(self, line):
        result = {}
        for name in self._feature_names:
            feature = self._feature_func(name)(line)
            if type(feature) == dict:
                result.update({"%s_%s" % (name, key) : value for
                               key, value in feature.iteritems()})
            else:
                result[name] = feature
        return result


    def features_dataframe(self, lines):
        lines = list(lines)
        if False not in [hasattr(line, 'id') and line.id is not None for line in lines]:
            return pd.DataFrame.from_dict({
                'line_%d' % l.id: self.line_features(l) for l in lines
            }, orient='index')
        else:
            for line in lines:
                self.temp_id(line)
            return pd.DataFrame.from_dict({
                'noid_%d' % line.temp_id: self.line_features(line) for line in lines
            }, orient='index')

    def temp_id(self, line):
        line.temp_id = self._next_temp_id
        self._next_temp_id += 1

    def lower_left_x(self, line):
        return line.x0

    def lower_left_y(self, line):
        return line.y0

    def space_count(self, line):
        return line.text.count(' ')

    def punctuation_count(self, line):
        return sum([line.text.count(c) for c in r",.?!"])

    def word_count(self, line):
        return len(line.text.split())

    def line_height(self, line):
        return line.y1 - line.y0

    def x_box(self, line):
        return line.box.x0 - line.x0

    def y_box(self, line):
        return line.y1 - line.box.y1

    def page_num(self, line):
        return line.page

    def all_caps_word_count(self, line):
        return len([w for w in line.text.split() if w.isupper()])

    def init_caps_word_count(self, line):
        return len([w for w in line.text.split() if w[0].isupper() and w[1:].islower()])

    def init_lower_word_count(self, line):
        return len([w for w in line.text.split() if w.islower()])

    def box_rank(self, line):
        return len([b for b in line.document.get_boxes() if b.y1 > line.box.y1
                    and b.page==line.page])

    def dict_word_count(self, line):
        line_words = [w.strip("\"';.:.!?") for w in line.text.split()]
        return len([w for w in line_words if w.lower() in self._dict])

    def box_phrases(self, line):
        result = {}
        for key, labels in self._box_phrases.iteritems():
            pattern = self._pattern_builder.field_pattern({'labels' : labels})

            result[key] = len([1 for line in line.box.get_lines()
                        if re.search(pattern, line.text) is not None])

        return result

    def contains_colon(self, line):
        return int(":" in line.text)


if __name__ == '__main__':
    parser = ArgumentParser(description='Compute features for lines')
    parser.add_argument('--settings', help='the path to the settings file',
                        default=None)
    parser.add_argument('--fix', help='repair a specific feature')

    args = parser.parse_args()
    settings_file = args.settings if args.settings else default_settings_file()
    settings = load_settings(settings_file)
    csv_directory = resolve_path(settings['csv_directory'], settings_file)

    map_tables(settings['fields'])
    session = db.session(settings)()

    pb = PatternBuilder(settings['substitutions'])

    all_fields = settings['fields'].copy()
    all_fields.update(settings['ignore_fields'])

    try:
        with open(settings['dictionary'], "r") as f:
            words = f.readlines()
            words = [w.strip() for w in words if w.islower()]
    except Exception:
        words = []

    fields = settings['fields']
    if args.fix:
        feature_names = {args.fix}
    else:
        feature_names = None

    #TODO : make this more generalizable!
    box_phrase_params = {}
    for field_name in fields:
        if "box_phrases" in fields[field_name]:
            box_phrase_params.update(fields[field_name]["box_phrases"])

    fb = FeatureBuilder(fields, words, feature_names, box_phrase_params, pb)

    query = session.query(Line).join(Document).\
        options(joinedload(Line.document, innerjoin=True)).\
        options(joinedload(Line.box, innerjoin=True)).\
        filter(Document.is_test == 0)

    features = fb.features_dataframe(query.all())

    if not args.fix:
        for field_name in settings['fields']:
            field = settings['fields'][field_name]
            if 'model' in field and field['model']:
                col_name = 'label_pattern_' + field_name
                features[col_name] = np.repeat(0, len(features))
                for document in session.query(Document).filter(Document.is_test == 0).all():
                    for page in range(document.num_pages):
                        for _, line in suggest_field_by_label(field, document, page, pb, all_fields):
                            features[col_name]['line_'+str(line.id)] = 1

    if args.fix:
        existing = pd.read_csv(path.join(csv_directory, 'training_features.csv'), index_col=0)
        for feature_name in feature_names:
            existing[feature_name] = features[feature_name]
        existing.to_csv(path.join(csv_directory, 'training_features.csv'), encoding='utf-8')
    else:
        features.to_csv(path.join(csv_directory, 'training_features.csv'), encoding='utf-8')
