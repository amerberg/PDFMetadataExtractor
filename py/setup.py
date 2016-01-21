from settings import load_settings, default_settings_file, load_labels
from argparse import ArgumentParser
from re import sub

import db
from schema import *

# PDFMiner includes
import os
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine
from pdfminer.layout import LTTextLineVertical, LTTextBoxVertical


def store_pdf_data(filename, directory, session, labels):
    try:
        with open(os.path.join(directory, filename)) as fp:
            parser = PDFParser(fp)
            pdf = PDFDocument(parser)
            parser.set_document(pdf)

            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)

            pages = PDFPage.create_pages(pdf)
            document = Document(filename=filename)
            for key in labels:
                setattr(document, key, labels[key])
            session.add(document)

            for i, page in enumerate(pages):
                # TODO: figure out how to get the number of pages directly from pages
                document.num_pages = i+1
                interpreter.process_page(page)
                layout = device.get_result()
                boxes = [obj for obj in layout if isinstance(obj, LTTextBox)]
                for b in boxes:
                    box = Box(document=document, page=i,
                              x0=b.bbox[0], y0=b.bbox[1],
                              x1=b.bbox[2], y1=b.bbox[3],
                              vertical=isinstance(b, LTTextBoxVertical))
                    session.add(box)
                    lines = [obj for obj in b
                             if isinstance(obj, LTTextLine)]
                    for l in lines:
                        text = sub(r'\(cid:\d+\)', "", l.get_text()).strip()
                        if len(text) > 0:
                            vertical = isinstance(l, LTTextLineVertical)
                            line = Line(box=box, document=document,
                                        x0=l.bbox[0], y0=l.bbox[1],
                                        x1=l.bbox[2], y1=l.bbox[3],
                                        text=text, vertical=vertical, page=i)
                            session.add(line)

            # do the whole file on one transaction so we can restart
            # easily if necessary
            session.commit()
    except Exception as e:
        print(filename, e)


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

        if not os.path.isabs(pdf_dir):
            pdf_dir = os.path.join(os.path.split(settings_file)[0],
                                   pdf_dir)
        filenames = os.listdir(pdf_dir)

        if not os.path.isabs(label_file):
            label_file = os.path.join(os.path.split(settings_file)[0],
                                      label_file)

        existing = [fn[0] for fn in session.query(Document.filename)]
        labels = load_labels(label_file)

        for filename in filenames:
            if filename not in existing:
                file_labels = labels[filename] if filename in labels else {}
                store_pdf_data(filename, pdf_dir, session, file_labels)
