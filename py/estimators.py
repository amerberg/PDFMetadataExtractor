import find_field
import pandas as pd
import numpy as np
import fields
from sklearn.base import BaseEstimator
import sys


class ModelWrapper(BaseEstimator):
    def __init__(self, field_name="", all_fields={}, feature_builder=None,
                 threshold=0, model_module="", model_class="", model_params=None):
        self.field_name = field_name
        self.all_fields = all_fields
        self.feature_builder = feature_builder
        self._estimator_type = "text"
        self.threshold = threshold
        self.model_class = model_class
        self.model_module = model_module
        self.model_params = model_params


    def get_features(self, X):
        features = []
        for document in X:
            try:
                features.append(document.features[self.field_name])
            except (KeyError, AttributeError):
                self._get_data(document)
                features.append(document.features[self.field_name])
        result=pd.concat([f for f in features if len(f) > 0]).sort_index()
        return result

    def get_scores(self, X):
        scores = []
        for document in X:
            try:
                scores.append(document.scores[self.field_name])
            except (KeyError, AttributeError):
                self._get_data(document)
                scores.append(document.scores[self.field_name])
        return pd.concat([s for s in scores if len(s) > 0])

    def get_formatted(self, X):
        formatted = []
        for document in X:
            try:
                formatted.append(document.formatted[self.field_name])
            except (KeyError, AttributeError):
                self._get_data(document)
                formatted.append(document.formatted[self.field_name])

        return pd.concat([f for f in formatted if len(f) > 0])

    def _get_data(self, document):
        handler = fields.get_handler(self.all_fields[self.field_name]['type'])
        field_name = self.field_name
        field = self.all_fields[field_name]
        fb = self.feature_builder
        pb = fb.pattern_builder()

        candidates = find_field.suggest_field(field, document, pb, self.all_fields)

        features = fb.features_dataframe([candidates], field_name)
        try:
            document.features[field_name] = features
        except AttributeError:
            document.features = {field_name: features}

        scores = {}
        for candidate in candidates:
            value = getattr(candidate.line.document, field_name)
            row_key = candidate.id()
            try:
                scores[row_key] = handler.compare(value, candidate.formatted)
            except TypeError:
                scores[row_key] = 0

        scores_series = pd.Series(scores)
        scores_series.index = features.index
        try:
            document.scores[field_name] = scores_series
        except AttributeError:
            document.scores = {field_name: scores_series}

        formatted = {}
        for candidate in candidates:
            row_key = candidate.id()
            formatted[row_key] = candidate.formatted
        format_series = pd.Series(formatted)
        format_series.index = features.index

        try:
            document.formatted[field_name] = format_series.sort_index()
        except AttributeError:
            document.formatted = {field_name: format_series}

    def fit(self, X, y):
        func = getattr(sys.modules[self.model_module], self.model_class)
        self.model_ = func(**self.model_params)
        self.model_.fit(self.get_features(X), np.ravel(self.get_scores(X).values))

    def predict(self, X):
        features = self.get_features(X)
        pred_scores = self.model_.predict(features)
        pred_scores = pd.Series(pred_scores, index=features.index)
        y = []
        formatted = self.get_formatted(X)

        for document in X:
            try:
                doc_scores = pred_scores.xs(document.id, level='document').sort_index()
                doc_formatted = formatted.xs(document.id, level='document').sort_index()
                index = doc_scores.idxmax()
                y.append(doc_formatted[index])
            except KeyError as e:
                y.append(None)
                pass

        return np.array(y)

    def score(self, X, y):
        handler = fields.get_handler(self.all_fields[self.field_name]['type'])
        y_pred = self.predict(X)
        scores = []
        for actual, pred in zip(y, y_pred):
            score = handler.compare(actual, pred)
            if score > self.threshold:
                scores.append(handler.compare(actual, pred))

        return sum(scores) / float(len([actual for actual in y if actual is not None]))

    def set_params(self, **params):
        if not params:
            return self
        valid_params = self.get_params(deep=True)
        model_params = {}
        wrapper_params = {}
        for key, value in params.iteritems():
            if key in valid_params:
                wrapper_params[key] = value
            else:
                model_params[key] = value

        wrapper_params['model_params'] = model_params
        BaseEstimator.set_params(self, **wrapper_params)
        return self