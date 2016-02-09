import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator
import importlib


class ModelWrapper(BaseEstimator):
    """ Wraper class for sklearn regressors.

    This class allows easy cross-validation with metrics directly relevant to
    the metadata prediction problem, rather than the score regression problem,
    which is only of indirect interest.
    """

    def __init__(self, field, threshold=1,
                 model_module="", model_class="", model_params={},
                 use_probability=False):
        """Set the field, threshold and model.


        :param field: The field to estimate
        :param threshold: The threshold above which partial credit should be granted.
        :param model_module: The name of the module in which the regressor is defined.
        :param model_class: The classname of the regressor.
        :param model_params: A dictionary of model parameters.
        :return: None
        """
        self.field = field
        self._estimator_type = "text"
        self.threshold = threshold
        self.model_class = model_class
        self.model_module = model_module
        self.model_params = model_params
        self._use_probability = use_probability


    def get_features(self, X):
        """ Get features for all candidates in a list of documents.

        :param X: A list of documents.
        :return: A pandas DataFrame of features.
        """

        features = []
        for document in X:
            try:
                features.append(document.features[self.field.name])
            except (KeyError, AttributeError):
                self._get_data(document)
                features.append(document.features[self.field.name])
        result = pd.concat([f for f in features if len(f) > 0]).sort_index()
        return result

    def get_scores(self, X):
        """ Get match scores for all candidates in a list of documents.

        :param X: A list of documents.
        :return: A pandas DataFrame of scores.
        """
        scores = []
        for document in X:
            try:
                scores.append(document.scores[self.field.name])
            except (KeyError, AttributeError):
                self._get_data(document)
                scores.append(document.scores[self.field.name])
        return pd.concat([s for s in scores if len(s) > 0])

    def get_values(self, X):
        """ Get the formatted values for the candidates in a document.

        :param X: A list of documents.
        :return: A pandas DataFrame of values.
        """
        values = []
        for document in X:
            try:
                values.append(document.values[self.field.name])
            except (KeyError, AttributeError):
                self._get_data(document)
                values.append(document.values[self.field.name])

        return pd.concat([f for f in values if len(f) > 0])

    def _get_data(self, document):
        """ Get all candidates for a document and store important data.

        :param document: A Document object.
        """
        field = self.field
        field_name = field.name

        candidates = field.get_candidates(document)

        features = field.features_dataframe([candidates])
        try:
            document.features[field_name] = features
        except AttributeError:
            document.features = {field_name: features}

        scores = {}
        for candidate in candidates:
            value = getattr(candidate.line.document, field_name)
            row_key = candidate.id
            try:
                scores[row_key] = field.compare(value, candidate.value)
            except TypeError:
                scores[row_key] = 0

        scores_series = pd.Series(scores)
        scores_series.index = features.index
        try:
            document.scores[field_name] = scores_series
        except AttributeError:
            document.scores = {field_name: scores_series}

        values = {candidate.id: candidate.value for candidate in candidates}
        values_series = pd.Series(values)
        values_series.index = features.index

        try:
            document.value[field_name] = values_series.sort_index()
        except AttributeError:
            document.value = {field_name: values_series}

    def fit(self, X, y):
        """Load, initialize, and fit the wrapped estimator"""
        module = importlib.import_module(self.model_module)
        func = getattr(module, self.model_class)
        self.model_ = func(**self.model_params)
        self.model_.fit(self.get_features(X), np.ravel(self.get_scores(X).values))

    def predict(self, X):
        """Predict candidate scores and guess the highest-scoring one."""
        features = self.get_features(X)
        method = self._model.predict_proba if self._use_probability else self.model_.predict
        pred_scores = method(features)
        pred_scores = pd.Series(pred_scores, index=features.index)
        y = []
        value = self.get_values(X)

        for document in X:
            try:
                doc_scores = pred_scores.xs(document.id, level='document').sort_index()
                doc_value = value.xs(document.id, level='document').sort_index()
                index = doc_scores.idxmax()
                y.append(doc_value[index])
            except KeyError as e:
                y.append(None)
                pass

        return np.array(y)

    def score(self, X, y):
        """Compute an accuracy score for predictions.

        "Partial credit" is awarded for matches scoring above self.threshold.
        :param X: A list of documents.
        :param y: A list-like object of values.
        :return: A numerical score.
        """
        y_pred = self.predict(X)
        scores = []
        for actual, pred in zip(y, y_pred):
            score = self.field.compare(actual, pred)
            if score > self.threshold:
                scores.append(score)

        return sum(scores) / float(len([actual for actual in y if actual is not None]))

    def set_params(self, **params):
        """Set parameters for the wrapper and the wrapped estimator.

        This method is required for compatibility with GridSearchCV.
        :param params: A dictionary of parameters for the wrapper and wrapped estimator.
         If a key doesn't match the name of a wrapper parameter, it is assumed to be
         for the wrapped estimator.
         TODO: it would be better to do what sklearn's pipeline does and provide some
         namespacing in case the wrapper and wrapped class share a parameter name
        :return: self
        """

        if not params:
            return self
        valid_params = self.get_params(deep=True)
        model_params = self.model_params
        wrapper_params = {}
        for key, value in params.iteritems():
            if key in valid_params:
                wrapper_params[key] = value
            else:
                model_params[key] = value

        wrapper_params['model_params'] = model_params
        BaseEstimator.set_params(self, **wrapper_params)
        return self