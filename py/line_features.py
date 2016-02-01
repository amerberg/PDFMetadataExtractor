from settings import load_settings, resolve_path, default_settings_file
from find_field import suggest_field, PatternBuilder
from argparse import ArgumentParser
from schema import *
import db
import pandas as pd
from sqlalchemy.orm import joinedload
from os import path
import field_types


class FeatureBuilder(object):

    def __init__(self, fields, dictionary, box_phrases={}, pattern_builder=None):
        feature_names = {}
        for name, field in fields.iteritems():
            try:
                feature_names[name] = field['features']
            except KeyError:
                pass
        self._feature_names = feature_names

        self._dict = dictionary
        self._box_phrases = box_phrases
        self._pattern_builder = pattern_builder

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
                 'contains_colon': self.contains_colon,
                 'length': self.length,
                 'digit_count': self.digit_count,
                 'alpha_count': self.alpha_count,
                 'rank_formatted': lambda x: self.rank(x, lambda c: c.formatted),
                 'hint_offset_x': lambda z: {c.id():getattr(c, 'hint_offset_x') for c in z},
                 'hint_offset_y': lambda z: {c.id():getattr(c, 'hint_offset_y') for c in z},
                 'hint_order': lambda z: {c.id():getattr(c, 'hint_order') for c in z}}
        return funcs[name]

    def doc_features(self, candidates, field_name):
        result = {candidate.id(): {} for candidate in candidates}
        for feature_name in self._feature_names[field_name]:
            feature = self._feature_func(feature_name)(candidates)
            for candidate in candidates:
                cid = candidate.id()
                if type(feature[cid]) == dict:
                    result[cid].update({"%s_%s" % (feature_name, key) : value for
                                        key, value in feature[cid].iteritems()})
                else:
                    result[cid][feature_name] = feature[cid]
        return result


    def features_dataframe(self, candidates_by_doc, field_name):
        features = {}
        for candidates in candidates_by_doc:
            features.update(self.doc_features(candidates, field_name))
        return pd.DataFrame.from_dict(features, orient='index')

    def lower_left_x(self, candidates):
        return {candidate.id(): candidate.line.x0 for candidate in candidates}

    def lower_left_y(self, candidates):
        return {candidate.id(): candidate.line.y0 for candidate in candidates}

    def space_count(self, candidates):
        return {candidate.id(): candidate.line.text.count(' ') for candidate in candidates}

    def punctuation_count(self, candidates):
        return {candidate.id(): sum([candidate.formatted.count(c) for c in r",.?!"]) for candidate in candidates}

    def word_count(self, candidates):
        return {candidate.id(): len(candidate.formatted) for candidate in candidates}

    def line_height(self, candidates):
        return {candidate.id(): candidate.line.y1 - candidate.line.y0 for candidate in candidates}

    def x_box(self, candidates):
        return {candidate.id(): candidate.line.box.x0 - candidate.line.x0 for candidate in candidates}

    def y_box(self, candidates):
        return {candidate.id(): candidate.line.y1 - candidate.line.box.y1 for candidate in candidates}

    def page_num(self, candidates):
        return {candidate.id(): candidate.line.page for candidate in candidates}

    def all_caps_word_count(self, candidates):
        return {candidate.id(): len([w for w in candidate.match.split() if w.isupper()]) for candidate in candidates}

    def init_caps_word_count(self, candidates):
        return {candidate.id(): len([w for w in candidate.match.split() if w[0].isupper() and w[1:].islower()]) for candidate in candidates}

    def init_lower_word_count(self, candidates):
        return {candidate.id(): len([w for w in candidate.match.split() if w.islower()]) for candidate in candidates}

    def box_rank(self, candidates):
        return {candidate.id(): len([b for b in candidate.line.document.get_boxes() if b.y1 > candidate.line.box.y1
                    and b.page==candidate.line.page]) for candidate in candidates}

    def dict_word_count(self, candidates):
        result = {}
        for candidate in candidates:
            line_words = [w.strip("\"';.:.!?") for w in candidate.match.split()]
            result[candidate.id()] = len([w for w in line_words if w.lower() in self._dict])
        return result

    def box_phrases(self, candidates):
        result = {candidate.id(): {} for candidate in candidates}
        for candidate in candidates:
            for key, labels in self._box_phrases.iteritems():
                pattern = self._pattern_builder.list_pattern(labels)

                result[candidate.id()][key] = len([1 for line in candidate.line.box.get_lines()
                            if re.search(pattern, line.text) is not None])

        return result

    def contains_colon(self, candidates):
        return {candidate.id(): int(":" in candidate.line.text) for candidate in candidates}

    def length(self, candidates):
        return {candidate.id(): len(candidate.formatted) for candidate in candidates}

    def digit_count(self, candidates):
        return {candidate.id(): sum([c.isdigit() for c in candidate.formatted]) for candidate in candidates}

    def alpha_count(self, candidates):
        return {candidate.id(): sum([c.isalpha() for c in candidate.formatted]) for candidate in candidates}

    def label_alignment(self, candidates):
        return {candidate.id(): candidate.label_alignment for candidate in candidates}

    def rank(self, candidates, key):
        values = sorted(list({key(c) for c in candidates}))
        return {c.id(): values.index(key(c)) for c in candidates}


if __name__ == '__main__':
    parser = ArgumentParser(description='Compute features for lines')
    parser.add_argument('--settings', help='the path to the settings file',
                        default=None)
    parser.add_argument('--fields', help='the fields to generate data for',
                        nargs='*', default=None)

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
    except KeyError:
        words = []

    fields = settings['fields']
    if args.fields is not None:
        fields = {field_name: fields[field_name] for field_name in args.fields}


    #TODO : make this more generalizable!
    box_phrases_params = {}
    for field_name in fields:
        if "box_phrases" in fields[field_name]:
            box_phrases_params.update(fields[field_name]["box_phrases"])

    fb = FeatureBuilder(fields, words, box_phrases_params, pb)
    candidates = {field_name: [] for field_name in fields}
    for document in session.query(Document).options(joinedload(Document.lines))\
            .filter(Document.is_test == 0):
        for field_name, field in fields.iteritems():
            if 'disabled' in field and field['disabled']:
                continue
            if getattr(document, field_name) is None:
                continue
            doc_candidates = suggest_field(field, document, pb, all_fields)
            candidates[field_name].append(doc_candidates)

    for field_name, field in fields.iteritems():

        if "model_file" not in field:
            continue

        features = fb.features_dataframe(candidates[field_name], field_name)
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
        score_df.to_csv(path.join(csv_directory, '%s_training_scores.csv' % field_name), encoding='utf-8')
