class Document(object):
    def __init__(self, filename='', num_pages=1):
        self.filename = filename
        self.num_pages = num_pages
        self._boxes = []
        self._lines = []

    def add_line(self, line):
        try:
            self._lines.append(line)
        except AttributeError:
            pass

    def add_box(self, box):
        try:
            self._boxes.append(box)
        except AttributeError:
            pass

    def get_lines(self):
        try:
            return self._lines
        except AttributeError:
            # constructors not called when loading from DB!
            return self.lines

    def get_boxes(self):
        try:
            return self._boxes
        except AttributeError:
            # constructors not called when loading from DB!
            return self.boxes

class Box(object):
    def __init__(self, **kwargs):
        self.document = kwargs['document']
        self.document.add_box(self)

        self.page = kwargs['page']
        self.x0 = kwargs['x0']
        self.y0 = kwargs['y0']
        self.x1 = kwargs['x1']
        self.y1 = kwargs['y1']
        self.vertical = kwargs['vertical']
        self._lines = []

    def add_line(self, line):
        try:
            self._lines.append(line)
        except AttributeError:
            pass

    def get_lines(self):
        try:
            return self._lines
        except AttributeError:
            # constructors not called when loading from DB!
            return self.lines


class Line(object):
    def __init__(self, **kwargs):
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