from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def engine(settings):
    return create_engine("%s://%s:%s@%s:%d/%s" % (settings['db_backend'],
                         settings['db_username'], settings['db_password'],
                         settings['db_server'], settings['db_port'],
                         settings['db_name']))


def session(settings):
    return sessionmaker(bind=engine(settings))