from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine
from pdfminer.layout import LTTextLineVertical, LTTextBoxVertical

from pdf_classes import *

import re


def extract_pdf_data(fp, labels={}, session=None):
    filename = fp.name.split()[-1]
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
    if session:
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
            if session:
                session.add(box)
            lines = [obj for obj in b
                     if isinstance(obj, LTTextLine)]
            for l in lines:
                text = re.sub(r'\(cid:\d+\)', "", l.get_text()).strip()
                if len(text) > 0:
                    vertical = isinstance(l, LTTextLineVertical)
                    line = Line(box=box, document=document,
                                x0=l.bbox[0], y0=l.bbox[1],
                                x1=l.bbox[2], y1=l.bbox[3],
                                text=text, vertical=vertical, page=i)
                    if session:
                        session.add(line)

    # do the whole file on one transaction so we can restart
    # easily if necessary
    if session:
        session.commit()
    return document
