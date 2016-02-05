import collections
import importlib
import abc
import re
import pandas as pd


class Field:
    def __init__(self, settings, name, data):
        self.name = name
        self.settings = settings
        self.labels = collections.defaultdict(list, data)['labels']
        #self._substitutions = collections.defaultdict(dict, data)['substitutions']
        self._data = data
        self._load_features()
        self._load_candidate_finders()

    def _load_features(self):
        self.features = {}
        infos = self._data['features']
        for name, info in infos.iteritems():
            module = importlib.import_module(info['module'])
            cls = info['class']
            params = info['parameters'] if 'parameters' in info else {}
            func = getattr(module, cls)
            self.features[name] = func(self, **params)

    def _load_candidate_finders(self):
        self._candidate_finders = {}
        for num, name in enumerate(collections.defaultdict(dict, self._data)['candidate_finders']):
            info = self._data['candidate_finders'][name]
            module = importlib.import_module(info['module'])
            cls = info['class']
            params = info['parameters']
            func = getattr(module, cls)
            self._candidate_finders[name] = func(self, num, self.settings.pattern_builder, **params)

    def get_candidates(self, document):
        return sum([finder.get_candidates(document) for finder in self._candidate_finders.values()], [])

    @abc.abstractmethod
    def patterns(self):
        return self.patterns

    def col_type(self):
        return self._col_type

    def get_value(self, value):
        return value

    def preprocess(self, text):
        return text

    def find_value(self, text):
        for pattern in self.patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None

    def compare(self, value1, value2):
        return value1 == value2

    def doc_features(self, candidates):
        result = {candidate.id: {} for candidate in candidates}
        for feature_name, feature in self.features.iteritems():
            values = feature.compute(candidates)
            for candidate in candidates:
                cid = candidate.id
                result[cid][feature_name] = values[cid]
        return result

    def features_dataframe(self, candidates_by_doc):
        features = {}
        for candidates in candidates_by_doc:
            features.update(self.doc_features(candidates))

        df = pd.DataFrame(features).transpose()
        if len(df) > 0:
            df.index.names = ['document', 'finder', 'num']
        return df
