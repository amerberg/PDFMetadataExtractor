from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


# TODO: allow configuration of string lengths
class Document(Base):
    __tablename__ = 'document'

    id = Column(Integer, primary_key=True)
    filename = Column(String(100), unique=True)
    num_pages = Column(Integer)
    boxes = relationship('Box', back_populates='document')
    lines = relationship('Line', back_populates='document')


class Box(Base):
    __tablename__ = 'box'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('document.id'))
    document = relationship('Document', back_populates='boxes')
    lines = relationship('Line', back_populates='box')
    # Positional information
    page = Column(Integer)
    x0 = Column(Float)
    y0 = Column(Float)
    x1 = Column(Float)
    y1 = Column(Float)
    vertical = Column(Boolean)



class Line(Base):
    __tablename__ = 'line'

    id = Column(Integer, primary_key=True)
    box_id = Column(Integer, ForeignKey('box.id'))
    box = relationship('Box', back_populates='lines')
    document_id = Column(Integer, ForeignKey('document.id'))
    document = relationship('Document', back_populates='lines')
    # Positional information
    x0 = Column(Float)
    y0 = Column(Float)
    x1 = Column(Float)
    y1 = Column(Float)
    vertical = Column(Boolean)
    # Content of the line
    text = Column(String(200))


def install_schema(engine):
    Base.metadata.create_all(engine)