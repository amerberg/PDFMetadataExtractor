from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def engine(settings):
    return create_engine("%s://%s:%s@%s:%d/%s" % (settings['backend'],
                         settings['username'], settings['password'],
                         settings['server'], settings['port'],
                         settings['name']))


def session(settings):
    return sessionmaker(bind=engine(settings))