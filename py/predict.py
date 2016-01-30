import line_features
import find_field
import numpy as np

class MetadataGuesser(object):
    def __init__(self, substitutions, fields, ignore_fields, dictionary):
        self._pattern_builder = find_field.PatternBuilder(substitutions)
        self._fields = fields
        self._ignore_fields = ignore_fields
        self._dictionary = dictionary
        self._all_fields = fields.copy()
        self._all_fields.update(ignore_fields)

    def predict(self, document):
        result = {}
        for field_name in self._fields:
            field = self._fields[field_name]

            if 'disabled' in field and field['disabled']:
                continue

            candidates = list(find_field.suggest_field_by_label(field, document,
                                                            self._pattern_builder,
                                                            self._all_fields))
            candidates = self.rank_candidates(candidates, field_name)

            result[field_name] = None
            for candidate in candidates:
                try:
                    result[field_name] = candidate.formatted
                    break
                except AttributeError:
                    pass

        return result


    def rank_candidates(self, candidates, field_name):
        if len(candidates) == 0:
            return []
        candidates = list(candidates)
        field = self._fields[field_name]
        if "model" not in field:
            try:
                return candidates
            except KeyError:
                return None
        else:
            model = field['model']
            try:
                fb = line_features.FeatureBuilder(self._fields, self._dictionary,
                                                  field['box_phrases'],
                                                  self._pattern_builder)
                features = fb.features_dataframe(candidates)
                scores = model.predict(features)
                index = scores.argsort()[::-1]
                return list(np.array(candidates)[index])
            except ValueError:
                #No suggestions!
                return None
