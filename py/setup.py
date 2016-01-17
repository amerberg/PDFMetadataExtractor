from settings import load_settings, default_settings_file
from argparse import ArgumentParser
import db
from schema import *

# PDFMiner includes
import os
from pdfminer.pdfparser import PDFParser, PDFSyntaxError
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine


def to_bytestring(s, enc='utf-8'):
    """Convert the given unicode string to a bytestring, using the standard encoding,
    unless it's already a bytestring"""
    if s:
        if isinstance(s, str):
            return s
        else:
            return s.encode(enc)


def extract_pdf_text(filename, directory, session):
    try:
        with open(os.path.join(directory, filename)) as fp:
            parser = PDFParser(fp)
            pdf = PDFDocument(parser)
            parser.set_document(pdf)

            document = Document(filename=filename)
            session.add(document)
            session.commit()


            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)

            for i, page in enumerate(PDFPage.create_pages(pdf)):
                interpreter.process_page(page)
                layout = device.get_result()
                boxes = [obj for obj in layout if isinstance(obj, LTTextBox)]:
                for b in boxes:
                    block = Block(document=document, page=i,
                                  x0=b.bbox[0], y0=b.bbox[1],
                                  x1=b.bbox[2], y1=b.bbox[3])
                    session.add(block)
                    session.commit()
                    lines = [obj for obj in b
                              if isinstance(obj, LTTextLine)]:
                    for l in lines:
                        line = Line(block=block,
                                      x0=l.bbox[0], y0=l.bbox[1],
                                      x1=l.bbox[2], y1=l.bbox[3],
                                      content=l.get_text())
                        session.add(line)
                    session.commit()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    argparser = ArgumentParser(description = 'Set up database')
    argparser.add_argument('--schema', help='install the schema', action='store_true')
    argparser.add_argument('--settings', help='the path to the settings file',
                           default=None)

    args = argparser.parse_args()
    settings_file = args.settings if args.settings else default_settings_file()
    settings = load_settings(settings_file)

    if args.schema:
        install_schema(db.engine(settings))
    else:
        Session = db.session(settings)
        session = Session()
        pdf_dir = settings['pdf_directory']
        if not os.path.isabs(pdf_dir):
            pdf_dir = os.path.join(os.path.split(settings_file)[0],
                                   pdf_dir)
        for filename in os.listdir(pdf_dir):
            extract_pdf_text(filename, pdf_dir, session)