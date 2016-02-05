import yaml
import collections, os, sys, pattern_builder
import sqlalchemy
import sqlalchemy.orm

class Settings:
    def __init__(self, filename):
        if filename is None:
            filename = self.default_file()
        self.filename = filename
        self._load_from_file()
        self._set_files()
        self._set_directories()
        self._pattern_builder = pattern_builder.PatternBuilder(self._data['substitutions'])
        self._extra_labels = self._data['extra_labels']

    def _load_from_file(self):
        with open(self.filename, 'r') as f:
            self._data = yaml.load(f)

    def session(self):
        import db
        maker = db.session(self._data['db'])
        return maker()

    def _set_files(self):
        files = collections.defaultdict(dict, self._data['files'])
        self._files = {key: self.resolve_path(value)
                       for key, value in files.iteritems()}

    def _set_directories(self):
        directories = collections.defaultdict(dict, self._data['directories'])
        self._directories = {key: self.resolve_path(value)
                             for key, value in directories.iteritems()}

    def resolve_path(self, path):
        settings_file = self.filename
        if not os.path.isabs(path):
            return os.path.join(os.path.split(settings_file)[0],
                                   path)
        else:
            return path

    def pattern_builder(self):
        return self._pattern_builder

    def default_file(self):
        return os.path.abspath("../settings.yml")

    def substitutions(self):
        return self._data['substitutions']

    def fields(self):
        return self._fields

    def get_directory(self, name):
        return self._directories[name]

    def _load_fields(self):
        self._fields = {}
        for name in collections.defaultdict(dict, self._data)['fields']:
            info = collections.defaultdict(None, self._data['fields'][name])
            if not info['disabled']:
                module = info['module']
                cls = info['class']
                params = info['parameters']
                func = getattr(sys.modules[module], cls)
                self._fields[name] = func(self, **params)

    def labels(self):
        with open(self._files['labels'], "r") as f:
            return yaml.load(f)

    # TODO: the following would probably fit better somewhere else
    def strip_labels(self, text):
        patterns = sum([field.labels() for field in self.fields().items()], [])
        patterns += self._extra_labels
        for pattern in patterns:
            if "labels" not in field:
                continue
            pattern = self.pattern_builder().list_pattern(patterns)
            if pattern is None:
                continue
            try:
                match = re.search(pattern, text)
                # TODO: do something less clumsy than joining on newlines...
                text = "\n".join([text[:match.start(0)], text[match.end(0):]])
            except AttributeError:
                # search returned None
                pass
        return text.split("\n")

    def map_tables(self):
        from schema import *
        from sqlalchemy import MetaData
        metadata = MetaData()
        mapper(Document, document_table(self.fields(), metadata),
               properties={'boxes': relationship(Box, back_populates='document'),
                           'lines': relationship(Line, back_populates='document')
                           })
        mapper(Box, box_table(self.fields(), metadata),
               properties={'document': relationship(Document, back_populates='boxes'),
                           'lines': relationship(Line, back_populates='box')
                           })
        mapper(Line, line_table(self.fields(), metadata),
               properties={'document': relationship(Document, back_populates='lines'),
                           'box': relationship(Box, back_populates='lines')
                           })
        return metadata


