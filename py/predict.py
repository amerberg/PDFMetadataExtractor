from find_field import PatternBuilder, get_field_value_by_label
from field_types import get_handler
import line_features
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
            handler = get_handler(field['type'])
            if 'disabled' in field and field['disabled']:
                continue

            suggestions = find_field.suggest_field_by_label(field, document,
                                                            self._pattern_builder,
                                                            self._all_fields)

            texts, line = self.choose_line(suggestions, field_name)
            for text in texts:
                formatted = handler.format(text)
                if formatted:
                    result[field_name] = formatted

        return result

    def choose_line(self, suggestions, field_name):
        field = self._fields[field_name]
        if "model" not in field:
            try:
                return suggestions.next()
            except StopIteration:
                return [], None
        else:
            model = field['model']
            try:
                matches, lines = zip(*suggestions)
                fb = line_features.FeatureBuilder(self._fields, self._dictionary,
                                                  field['box_phrases'],
                                                  self._pattern_builder)
                features = fb.features_dataframe(lines)
                scores = model.predict(features)
                index = scores.argmax()
                return matches[index], lines[index]
            except ValueError:
                #No suggestions!
                return [], None
