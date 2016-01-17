from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


# TODO: allow setting string lengths
class Document(Base):
    __tablename__ = 'document'

    id = Column(Integer, primary_key=True)
    filename = Column(String(100), unique=True)
    num_pages = Column(Integer)
    blocks = relationship("Block", back_populates='document')


# TODO: do we need to think about vertical text?!?!

class Block(Base):
    __tablename__ = 'block'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('document.id'))
    document = relationship("Document", back_populates="blocks")
    lines = relationship("Line", back_populates='block')
    # Positional information
    page = Column(Integer)
    x0 = Column(Float)
    y0 = Column(Float)
    x1 = Column(Float)
    y1 = Column(Float)


class Line(Base):
    __tablename__ = 'line'

    id = Column(Integer, primary_key=True)
    block_id = Column(Integer, ForeignKey('block.id'))
    block = relationship("Block", back_populates="lines")
    # Positional information
    x0 = Column(Float)
    y0 = Column(Float)
    x1 = Column(Float)
    y1 = Column(Float)
    content = Column(String(200))


def install_schema(engine):
    Base.metadata.create_all(engine)