from settings import load_settings, resolve_path, default_settings_file
from find_field import suggest_field_by_label, PatternBuilder
from argparse import ArgumentParser
from schema import *
import db
import pandas as pd
from sqlalchemy.orm import joinedload
from os import path
import field_types


class FeatureBuilder(object):

    def __init__(self, fields, dictionary, box_phrases={}, pattern_builder=None):
        self._feature_names = set(sum([fields[f]["features"] for f in fields
                                 if "features" in fields[f]], []))
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
                 'contains_colon': self.contains_colon,
                 'length': self.length,
                 'digit_count': self.digit_count,
                 'alpha_count': self.alpha_count}
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


    def features_dataframe(self, candidates):
        return pd.DataFrame.from_dict({
            c.id(): self.line_features(c) for c in candidates
        }, orient='index')

    def lower_left_x(self, candidate):
        return candidate.line.x0

    def lower_left_y(self, candidate):
        return candidate.line.y0

    def space_count(self, candidate):
        return candidate.line.text.count(' ')

    def punctuation_count(self, candidate):
        return sum([candidate.formatted.count(c) for c in r",.?!"])

    def word_count(self, candidate):
        return len(candidate.formatted)

    def line_height(self, candidate):
        return candidate.line.y1 - candidate.line.y0

    def x_box(self, candidate):
        return candidate.line.box.x0 - candidate.line.x0

    def y_box(self, candidate):
        return candidate.line.y1 - candidate.line.box.y1

    def page_num(self, candidate):
        return candidate.line.page

    def all_caps_word_count(self, candidate):
        return len([w for w in candidate.match.split() if w.isupper()])

    def init_caps_word_count(self, candidate):
        return len([w for w in candidate.match.split() if w[0].isupper() and w[1:].islower()])

    def init_lower_word_count(self, candidate):
        return len([w for w in candidate.match.split() if w.islower()])

    def box_rank(self, candidate):
        line = candidate.line
        return len([b for b in line.document.get_boxes() if b.y1 > line.box.y1
                    and b.page==line.page])

    def dict_word_count(self, candidate):
        line_words = [w.strip("\"';.:.!?") for w in candidate.match.split()]
        return len([w for w in line_words if w.lower() in self._dict])

    def box_phrases(self, candidate):
        result = {}
        for key, labels in self._box_phrases.iteritems():
            pattern = self._pattern_builder.field_pattern({'labels' : labels})

            result[key] = len([1 for line in candidate.line.box.get_lines()
                        if re.search(pattern, line.text) is not None])

        return result

    def contains_colon(self, candidate):
        return int(":" in candidate.line.text)

    def length(self, candidate):
        return len(candidate.formatted)

    def digit_count(self, candidate):
        return sum([c.isdigit() for c in candidate.formatted])

    def alpha_count(self, candidate):
        return sum([c.isalpha() for c in candidate.formatted])

    def label_alignment(self, candidate):
        return candidate.label_alignment

if __name__ == '__main__':
    parser = ArgumentParser(description='Compute features for lines')
    parser.add_argument('--settings', help='the path to the settings file',
                        default=None)

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

    #TODO : make this more generalizable!
    box_phrases_params = {}
    for field_name in fields:
        if "box_phrases" in fields[field_name]:
            box_phrases_params.update(fields[field_name]["box_phrases"])

    fb = FeatureBuilder(fields, words, box_phrases_params, pb)
    candidates = {field_name: set([]) for field_name in fields}
    for document in session.query(Document).options(joinedload(Document.lines))\
            .filter(Document.is_test == 0):
        for field_name, field in settings['fields'].iteritems():
            if 'disabled' in field and field['disabled']:
                continue
            doc_candidates = suggest_field_by_label(field, document, pb, all_fields)
            candidates[field_name].update(set(doc_candidates))


    for field_name, field in fields.iteritems():

        if "model" not in field:
            continue
        columns = field['features']
        if "model" not in field:
            continue
        try:
            columns.remove('box_phrases')
            columns += ['box_phrases_%s' % phrase for phrase in field['box_phrases']]
        except ValueError:
            pass

        features = fb.features_dataframe(candidates[field_name])
        features.to_csv(path.join(csv_directory, '%s_training_features.csv' % field_name), encoding='utf-8')

        col_name = "%s_score" % field_name
        handler = field_types.get_handler(field['type'])
        scores={}
        sym_scores={}
        for candidate in candidates[field_name]:
            value = getattr(candidate.line.document, field_name)
            row_key = candidate.id()
            sym_scores[row_key] = handler.compare(value, candidate.formatted)


        score_df = pd.DataFrame({col_name: scores, 'sym_%s' % col_name: sym_scores}).sort_index()
        score_df.to_csv(path.join(csv_directory, '%s_training_scores.csv' % field_name), encoding='utf-8')
