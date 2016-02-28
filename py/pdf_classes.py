class Document(object):
    """Class that represents a single PDF document."""
    def __init__(self, filename='', num_pages=1, is_test=False):
        self.filename = filename
        self.num_pages = num_pages
        self.is_test = is_test
        self._boxes = []
        self._lines = []

    def add_line(self, line):
        """Add a line to a document that hasn't been loaded from the database."""
        try:
            self._lines.append(line)
        except AttributeError:
            #This was loaded from the database and so the constructor never ran.
            pass

    def add_box(self, box):
        """Add a box to a document that wasn't loaded from the database."""
        try:
            self._boxes.append(box)
        except AttributeError:
            pass

    def get_lines(self):
        """Get all lines for this document, regardless of how it was loaded."""
        try:
            # Not loaded from the database.
            return self._lines
        except AttributeError:
            # Constructors not called when loading from DB!
            return self.lines

    def get_boxes(self):
        """Get all boxes for the document, regardless of how it was loaded."""
        try:
            # Not loaded from database.
            return self._boxes
        except AttributeError:
            # Constructors not called when loading from DB!
            return self.boxes

class Box(object):
    """Class that represents a single box, as returned by PDFMiner."""
    def __init__(self, **kwargs):
        self.document = kwargs['document']
        self.document.add_box(self)

        self.page = kwargs['page']
        self.x0 = kwargs['x0']
        self.y0 = kwargs['y0']
        self.x1 = kwargs['x1']
        self.y1 = kwargs['y1']
        # TODO: Vertical isn't really implemented yet, even though we store it here.
        self.vertical = kwargs['vertical']
        self._lines = []

    def add_line(self, line):
        """Add a line to a box that wasn't loaded from the database."""
        try:
            self._lines.append(line)
        except AttributeError:
            pass

    def get_lines(self):
        """Get all lines, regardless of how this class was created."""
        try:
            return self._lines
        except AttributeError:
            # constructors not called when loading from DB!
            return self.lines


class Line(object):
    """Class that represents a single line returned by PDFMiner."""
    def __init__(self, **kwargs):
        """Set bounding box, document, and text."""
        # TODO: Define arguments for this function explicitly.
        self.document = kwargs['document']
        self.document.add_line(self)
        self.box = kwargs['box']
        self.box.add_line(self)
        self.page = kwargs['page']
        self.x0 = kwargs['x0']
        self.y0 = kwargs['y0']
        self.x1 = kwargs['x1']
        self.y1 = kwargs['y1']
        self.vertical = kwargs['vertical']
        self.text = kwargs['text']