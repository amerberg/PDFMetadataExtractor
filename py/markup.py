from settings import Settings
from argparse import ArgumentParser
import os

# PDFMiner includes
from pdfminer.pdfparser import PDFParser, PDFSyntaxError
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTChar

#PDF writing
from reportlab.pdfgen import canvas
from pdfrw import PdfReader, PdfWriter, PageMerge


def make_rectangle(canvas, bbox):
    canvas.rect(bbox[0], bbox[1], bbox[2]-bbox[0],
           bbox[3]-bbox[1])


def mark_pdf(clean_path, marked_path):
    """Draw rectangles around the boxes, lines, and characters in a document."""
    try:
        with open(os.path.join(clean_path)) as fp:
            parser = PDFParser(fp)
            pdf = PDFDocument(parser)
            parser.set_document(pdf)

            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)

            marked_dir, marked_fn = os.path.split(marked_path)
            rect_file = os.path.join(marked_dir, ".rects." + marked_fn)

            c = canvas.Canvas(rect_file)

            for i, page in enumerate(PDFPage.create_pages(pdf)):
                interpreter.process_page(page)
                layout = device.get_result()
                boxes = [obj for obj in layout if isinstance(obj, LTTextBox)]
                for box in boxes:
                    c.setLineWidth(1)
                    c.setStrokeColorRGB(1, 0, 0)
                    make_rectangle(c, box.bbox)
                    lines = [obj for obj in box
                             if isinstance(obj, LTTextLine)]
                    for line in lines:
                        c.setLineWidth(0.5)
                        c.setStrokeColorRGB(0, 1, 0)
                        make_rectangle(c, line.bbox)
                        for char in line:
                            if isinstance(char, LTChar):
                                c.setLineWidth(0.3)
                                c.setStrokeColorRGB(0,0,1)
                                make_rectangle(c, char.bbox)
                c.showPage()
            c.save()

        pdf_content = PdfReader(clean_path)
        for i,page in enumerate(pdf_content.pages):
            rects = PageMerge().add(PdfReader(rect_file).pages[i])[0]
            PageMerge(page).add(rects).render()

        PdfWriter().write(marked_path, pdf_content)
        os.remove(rect_file)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    argparser = ArgumentParser(description = 'Mark blocks, lines and characters in a PDF')
    argparser.add_argument('filename', help='the name of the file to mark up')
    argparser.add_argument('--settings', help='the path to the settings file',
                           default=None)

    args = argparser.parse_args()
    settings = Settings(args.settings)

    pdf_dir = settings.get_directory('pdf')
    marked_pdf_dir = settings.get_directory('marked_pdf')

    clean_path = os.path.join(pdf_dir, args.filename)
    marked_path = os.path.join(marked_pdf_dir, args.filename)

    mark_pdf(clean_path, marked_path)