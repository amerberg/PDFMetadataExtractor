import yaml
import collections
import os
import importlib
import pattern_builder
import re


class Settings:
    """Represent  settings and do related things.

    Settings are stored in a YAML

    """
    def __init__(self, filename=None):
        """Load settings from a file.

        Loads the settings from the YAML file given by filename (or a default path
        if none is specified).  Initialize all fields and the pattern builder.
        Store all files and directories as absolute paths.
        """

        if filename is None:
            filename = self.default_file()
        self.filename = filename
        self._load_from_file()
        self.pattern_builder = pattern_builder.PatternBuilder(self._data['substitutions'])

        self._load_fields()
        self._set_files()
        self._set_directories()
        self._extra_labels = self._data['extra_labels']
        self.test_proportion = self._data['test_proportion']

    def _load_from_file(self):
        """Load the settings from the given filename."""
        with open(self.filename, 'r') as f:
            self._data = yaml.load(f)

    def session(self):
        """Get a SQLAlchemy session object for the database specified."""
        import sqlalchemy.orm
        maker = sqlalchemy.orm.sessionmaker(bind=self.engine())
        return maker()

    def engine(self):
        """Get a SQLAlchemy engine object for the specified database."""
        import sqlalchemy
        db = self._data['db']
        address = "%s://%s:%s@%s:%d/%s" % (db['backend'], db['username'],
                                           db['password'], db['server'],
                                           db['port'], db['name'])
        if "charset" in db:
            address += "?charset=%s" % db['charset']
        return sqlalchemy.create_engine(address)

    def _set_files(self):
        """Get filenames from  settings dictionary and store absolute paths."""
        files = collections.defaultdict(dict, self._data['files'])
        self._files = {key: self.resolve_path(value)
                       for key, value in files.iteritems()}

    def _set_directories(self):
        """Store absolute paths for directories."""
        directories = collections.defaultdict(dict, self._data['directories'])
        self._directories = {key: self.resolve_path(value)
                             for key, value in directories.iteritems()}

    def resolve_path(self, path):
        """Convert a filename from the settings file to an absolute path.

        Absolute paths are left as is. Relative paths are assumed to be
        relative to the settings file.
        """

        settings_file = self.filename
        if not os.path.isabs(path):
            return os.path.join(os.path.split(settings_file)[0], path)
        else:
            return path

    def default_file(self):
        """A default location for the settings YAML file."""
        return os.path.abspath("../settings.yml")

    def substitutions(self):
        """The allowable substitutions to be used when generating patterns."""
        return self._data['substitutions']


    def get_directory(self, name):
        """Retrieve the absolute path for a directory."""
        return self._directories[name]

    def get_file(self, name):
        """Retrieve the absolute path for a file."""
        return self._files[name]

    def _load_fields(self):
        """Load fields specified in the settings file."""
        self.fields = {}
        for name in self._data['fields']:
            info = self._data['fields'][name]
            if 'disabled' not in info or not info['disabled']:
                module = importlib.import_module(info['module'])
                cls = info['class']
                func = getattr(module, cls)
                params = info.get('parameters', {})
                self.fields[name] = func(self, name, info, **params)

    def load_labels(self):
        """Load correct metadata labels from a YAML file.

        This is called when populating the database.
        """

        with open(self.get_file('label'), "r") as f:
            return yaml.load(f)

    # TODO: the following would probably fit better somewhere else
    def strip_labels(self, text):
        """ Remove all field labels from some text.
        :param text: A string from which to remove labels.
        :return: A list of strings formed by removing labels from the text.
        """
        labels = sum([field.labels for field in self.fields.values()], self._extra_labels)
        pattern = self.pattern_builder.list_pattern(labels)
        if pattern is None:
            return text
        return re.split(pattern, text)

    def map_tables(self):
        """ Map the Document, Box, and Line classes to their SQL tables."""
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
