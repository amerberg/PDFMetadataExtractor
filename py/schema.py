#from pdf_classes import *
from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy import Integer, Float, Boolean
#from sqlalchemy.orm import relationship, mapper
from fields import *

# TODO: allow configuration of string lengths
def document_table(fields, metadata):
    return Table('document', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('filename', String(255), unique=True),
                 Column('num_pages', Integer),
                 Column('is_test', Boolean, index=True),
                 *(Column(fn, field.col_type) for fn, field in fields.iteritems())
              )

def box_table(metadata):
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

def line_table(metadata):
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
