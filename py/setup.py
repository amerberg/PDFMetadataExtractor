from settings import load_settings, default_settings_file, load_labels, resolve_path
from argparse import ArgumentParser
from extract import extract_pdf_data

import db
from schema import *
import os


if __name__ == "__main__":
    parser = ArgumentParser(description='Set up database')
    parser.add_argument('--schema', help='install the schema', action='store_true')
    parser.add_argument('--settings', help='the path to the settings file',
                           default=None)

    args = parser.parse_args()
    settings_file = args.settings if args.settings else default_settings_file()
    settings = load_settings(settings_file)

    if args.schema:
        install_schema(db.engine(settings), settings['fields'])
    else:
        map_tables(settings['fields'])
        Session = db.session(settings)
        session = Session()
        pdf_dir = settings['pdf_directory']
        label_file = settings['label_file']

        pdf_dir = resolve_path(pdf_dir, settings_file)

        label_file = resolve_path(label_file, settings_file)

        existing = [fn[0] for fn in session.query(Document.filename)]
        labels = load_labels(label_file)

        for filename in os.listdir(pdf_dir):
            if filename not in existing:
                file_labels = labels[filename] if filename in labels else {}

                try:
                    with open(os.path.join(pdf_dir, filename), "r") as fp:
                        extract_pdf_data(fp, file_labels, session)
                except Exception as e:
                    print (filename, e)

