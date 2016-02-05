import collections
import sys
import abc
import re
import pandas as pd


class Field:
    def __init__(self, settings, name, data):
        self.name = name
        self.settings = settings
        self._labels = collections.defaultdict(list, data)['labels']
        self._substitutions = collections.defaultdict(dict, data)['substitutions']
        self._load_features()
        self._data = data

    def labels(self):
        return self._labels()

    def features(self):
        return self._features()

    def _load_features(self):
        self.features = {}
        for name in collections.defaultdict(dict, self._data)['features']:
            info = self._data['features'][name]
            module = info['module']
            cls = info['class']
            params = info['parameters']
            func = getattr(sys.modules[module], cls)
            self.features[name] = func(self, **params)

    def _load_candidate_generators(self):
        self._candidate_generators = {}
        for name in collections.defaultdict(dict, self._data)['candidate_generators']:
            info = self._data['candidate_generators'][name]
            module = info['module']
            cls = info['class']
            params = info['parameters']
            func = getattr(sys.modules[module], cls)
            self.candidate_generators[name] = func(self, **params)

    @abc.abstractmethod
    def patterns(self):
        return self.patterns

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

    def doc_features(self, candidates):
        result = {candidate.id(): {} for candidate in candidates}
        for feature_name, feature in self.features.iteritems():
            values = feature.compute(candidates)
            for candidate in candidates:
                cid = candidate.id()
                result[cid][feature_name] = values[cid]
        return result

    def features_dataframe(self, candidates_by_doc):
        features = {}
        for candidates in candidates_by_doc:
            features.update(self.doc_features(candidates))

        df = pd.DataFrame(features).transpose()
        if len(df) > 0:
            df.index.names = ['document', 'line', 'generator', 'num']
        return df
