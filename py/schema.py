from pdf_classes import *
from sqlalchemy import Column, ForeignKey, Table, MetaData
from sqlalchemy import Integer, String, Float, Boolean
from sqlalchemy.orm import relationship, mapper
from field_types import *

# TODO: allow configuration of string lengths
def document_table(fields, metadata):
    return Table('document', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('filename', String(255), unique=True),
                 Column('num_pages', Integer),
                 Column('is_test', Boolean, index=True),
                 *(Column(fn, get_handler(fields[fn]['type']).col_type()) for fn in fields)
              )

def box_table(fields, metadata):
    return Table('box', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('document_id', Integer, ForeignKey('document.id')),
                 Column('page', Integer),
                 Column('x0', Float),
                 Column('y0', Float),
                 Column('x1', Float),
                 Column('y1', Float),
                 Column('vertical', Boolean)
                 )

def line_table(fields, metadata):
    return Table('line', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('document_id', Integer, ForeignKey('document.id')),
                 Column('box_id', Integer, ForeignKey('box.id')),
                 Column('page', Integer),
                 Column('x0', Float),
                 Column('y0', Float),
                 Column('x1', Float),
                 Column('y1', Float),
                 Column('vertical', Boolean),
                 Column('text', String(1023))
                 )

def map_tables(fields):
    metadata = MetaData()
    mapper(Document, document_table(fields, metadata),
           properties={'boxes': relationship(Box, back_populates='document'),
                       'lines': relationship(Line, back_populates='document')
                       })
    mapper(Box, box_table(fields, metadata),
           properties={'document': relationship(Document, back_populates='boxes'),
                       'lines': relationship(Line, back_populates='box')
                       })
    mapper(Line, line_table(fields, metadata),
           properties={'document': relationship(Document, back_populates='lines'),
                       'box': relationship(Box, back_populates='lines')
                       })
    return metadata

def install_schema(engine, fields):
    metadata = map_tables(fields)
    metadata.create_all(engine)
