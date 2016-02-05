import yaml
import collections
import os
import importlib
import pattern_builder
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Settings:
    def __init__(self, filename):
        if filename is None:
            filename = self.default_file()
        self.filename = filename
        self._load_from_file()
        self.pattern_builder = pattern_builder.PatternBuilder(self._data['substitutions'])

        self._load_fields()
        self._set_files()
        self._set_directories()
        self._extra_labels = self._data['extra_labels']

    def _load_from_file(self):
        with open(self.filename, 'r') as f:
            self._data = yaml.load(f)

    def session(self):
        maker = sessionmaker(bind=self.engine())
        return maker()

    def engine(self):
        db = self._data['db']
        return create_engine("%s://%s:%s@%s:%d/%s?charset=utf8" % (db['backend'],
                             db['username'], db['password'],
                             db['server'], db['port'],
                             db['name']))
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
            return os.path.join(os.path.split(settings_file)[0], path)
        else:
            return path

    def default_file(self):
        return os.path.abspath("../settings.yml")

    def substitutions(self):
        return self._data['substitutions']


    def get_directory(self, name):
        return self._directories[name]

    def get_file(self, name):
        return self._files[name]

    def _load_fields(self):
        self.fields = {}
        for name in collections.defaultdict(dict, self._data)['fields']:
            info = self._data['fields'][name]
            if 'disabled' not in info or not info['disabled']:
                module = importlib.import_module(info['module'])
                cls = info['class']
                func = getattr(module, cls)
                params = info['parameters'] if 'parameters' in info else {}
                self.fields[name] = func(self, name, info, **params)

    def load_labels(self):
        with open(self.get_file('label'), "r") as f:
            return yaml.load(f)

    # TODO: the following would probably fit better somewhere else
    def strip_labels(self, text):
        patterns = sum([field.labels for field in self.fields.values()], [])
        patterns += self._extra_labels
        for pattern in patterns:
            pattern = self.pattern_builder.list_pattern(patterns)
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
        from schema import document_table, box_table, line_table
        from sqlalchemy import MetaData
        from sqlalchemy.orm import mapper, relationship
        from pdf_classes import Document, Box, Line

        metadata = MetaData()
        mapper(Document, document_table(self.fields, metadata),
               properties={'boxes': relationship(Box, back_populates='document'),
                           'lines': relationship(Line, back_populates='document')
                           })
        mapper(Box, box_table(metadata),
               properties={'document': relationship(Document, back_populates='boxes'),
                           'lines': relationship(Line, back_populates='box')
                           })
        mapper(Line, line_table(metadata),
               properties={'document': relationship(Document, back_populates='lines'),
                           'box': relationship(Box, back_populates='lines')
                           })
        return metadata


