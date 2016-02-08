import importlib
import abc
import re
import pandas as pd
import os


class Field:
    """The base class for metadata field types.

    This class must be extended to provide functionality for specific datatypes.
    It defines certain basic functionaity that is likely to be common to
    various types.

    """
    def __init__(self, settings, name, data):
        """Set basic field properties."""
        self.name = name
        self.settings = settings
        self.labels = data['labels'] if 'labels' in data else []
        self._data = data
        self._load_features()
        self._load_candidate_finders()

    def _load_features(self):
        """Load the fields features as defined in the settings."""
        self.features = {}
        infos = self._data['features']
        for name, info in infos.iteritems():
            module = importlib.import_module(info['module'])
            cls = info['class']
            params = info['parameters'] if 'parameters' in info else {}
            func = getattr(module, cls)
            self.features[name] = func(self, **params)

    def _load_candidate_finders(self):
        """Load the field's candidate finders as defined in the settings"""
        self._candidate_finders = {}
        for num, name in enumerate(self._data['candidate_finders']):
            info = self._data['candidate_finders'][name]
            module = importlib.import_module(info['module'])
            cls = info['class']
            params = info['parameters']
            func = getattr(module, cls)
            self._candidate_finders[name] = func(self, num, **params)

    def get_candidates(self, document):
        """Return all candidates identified by all of the candidate finders"""
        return sum([finder.get_candidates(document) for finder in self._candidate_finders.values()], [])

    @abc.abstractmethod
    def patterns(self):
        """Abstract method returns a list of patterns that match field values."""
        return self.patterns

    def col_type(self):
        """Return the database column type to be used to represent this field."""
        return self._col_type

    def preprocess(self, text):
        """Preprocess a string before looking for a value."""
        return text

    def find_value(self, text):
        """Find a substring of a given string that likely to contain a field value"""
        for pattern in self.patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None

    def get_value(self, text):
        """Converts text to a formatted value"""
        return text

    def compare(self, value1, value2):
        """Compare two different values of this field"""
        return float(value1 == value2)

    def doc_features(self, candidates):
        """Compute all features for a list of candidates."""
        result = {candidate.id: {} for candidate in candidates}
        for feature_name, feature in self.features.iteritems():
            values = feature.compute(candidates)
            for candidate in candidates:
                cid = candidate.id
                result[cid][feature_name] = values[cid]
        return result

    def features_dataframe(self, candidates_by_doc):
        """Compute a dataframe of features for candidates.
        :candidates_by_doc: A dictionary, whose keys are document ids and whose
        values are lists of candidates in the corresponding documents.

        """

        features = {}
        for candidates in candidates_by_doc:
            features.update(self.doc_features(candidates))

        df = pd.DataFrame(features).transpose()
        if len(df) > 0:
            df.index.names = ['document', 'finder', 'num']
        return df

    def _check_model(self):
        if "model_definition" in self['data']:
            import pickle
            directory = self.settings.get_directory('pickle')
            model_file = self['data']['model_definition'] + ".pkl"
            with open(os.path.join(directory, model_file)) as f:
                self._model = pickle.load(f)

    def predict(self, document):
        self._check_model()
        if self._model is not None:
            return self._model.predict([document])
        else:
            try:
                return self.get_candidates(document)[0].value
            except KeyError:
                return None



