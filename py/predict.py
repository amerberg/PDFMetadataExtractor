from find_field import PatternBuilder, get_field_value_by_label
from field_types import get_handler
import line_features
import numpy as np
import find_field

class MetadataGuesser(object):
    def __init__(self, substitutions, fields, ignore_fields, dictionary):
        self._pattern_builder = PatternBuilder(substitutions)
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
            if "model" not in field:
                result[field_name] = self.predict_by_labels(document, field_name)
            else:
                result[field_name] = self.predict_by_model(document, field_name)
        return result

    def predict_by_labels(self, document, field_name):
        field = self._fields[field_name]
        extracted = get_field_value_by_label(field, document, 0, self._pattern_builder, self._all_fields)

        try:
            return get_handler(field['type']).format(extracted)
        except TypeError:
            return None

    def predict_by_model(self, document, field_name):
        field = self._fields[field_name]
        fb = line_features.FeatureBuilder(self._fields, self._dictionary,
                                          field['features'], field['box_phrases'], self._pattern_builder)
        lines = document.get_lines()
        features = fb.features_dataframe(lines)

        col_name = 'label_pattern_' + field_name
        features[col_name] = np.repeat(0, len(features))

        for page in range(document.num_pages):
            suggestions = find_field.suggest_field_by_label(field, document, page, self._pattern_builder, self._all_fields)
            for _, line in suggestions:
                try:
                    key = 'noid_%d' % line.temp_id
                except:
                    key = 'line_%d' % line.id
                features[col_name][key] = 1

        scores = field['model'].predict(features)

        num = min(len(scores), 5)
        bests = np.argpartition(scores, -num)[-num:]
        sorted_bests = np.argsort(scores[bests])[::-1]

        for ind in bests[sorted_bests]:
            line = lines[ind]

            texts = find_field.strip_labels(line.text, self._all_fields, self._pattern_builder)
            handler = get_handler(field['type'])
            texts = [handler.preprocess(text) for text in texts]
            values = [handler.find_value(text) for text in texts]

            for value in values:
                if value is not None:
                    return handler.format(value)

        return None



