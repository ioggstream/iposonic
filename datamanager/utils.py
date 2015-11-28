"""Data manager decorators and paradigms."""
from __future__ import unicode_literals
from sqlalchemy.ext.declarative import DeclarativeMeta

from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy import orm

from exc import *

def jsonize(fn):
    """jsonize decorator."""
    def tmp(self, *args, **kwds):
        item = fn(self, *args, **kwds)
        print "running jsonize on %s" % item

        if item:
            if isinstance(item, list):
                return [x.json() for x in item]
            else:
                return item.json()
        return None
    tmp.__name__ = fn.__name__
    return tmp

def synchronized(lock):
    """ Synchronization decorator. """

    def wrap(f):
        def newFunction(*args, **kw):
            self = args[0]
            lock.acquire()
            self.log.info("lock acquired")
            try:
                return f(*args, **kw)
            finally:
                lock.release()
                self.log.info("lock released")
        return newFunction
    return wrap

def connectable(fn):
    """add transactional semantics to a method.

    """
    def connect(self, *args, **kwds):
        session = self.Session()
        kwds['session'] = session
        try:
            ret = fn(self, *args, **kwds)
            return ret
        except (ProgrammingError, OperationalError) as e:
            self.log.exception(
                "Corrupted database: removing and recreating")
            self.reset()
        except orm.exc.NoResultFound as e:
            # detailed logging for NoResultFound isn't needed.
            # just propagate the exception
            raise EntryNotFoundException(e)
        except Exception as e:
            #if len(args): ret = to_unicode(args[0])
            #else: ret = ""
            self.log.exception("error: %r, %r"  % (args, kwds) )
            raise
    connect.__name__ = fn.__name__
    return connect

def transactional(fn):
    """add transactional semantics to a method.

    """
    def transact(self, *argss, **kwds):
        session = self.Session()
        kwds['session'] = session
        self.log.info("transact: %r, %r, %r" % (argss, kwds, {'fn': fn}))
        try:
            self.log.info("starting transaction")
            ret = fn(self, *argss, **kwds)
            session.commit()
            self.log.info("end transaction")
            return ret
        except orm.exc.NoResultFound as e:
            # detailed logging for NoResultFound isn't needed.
            # just propagate the exception
            raise EntryNotFoundException(e)
        except (ProgrammingError, OperationalError) as e:
            session.rollback()
            self.log.exception(
                "Corrupted database: removing and recreating")
            self.reset()
        except Exception as e:
            session.rollback()
            #if len(args): ret = to_unicode(args[0])
            #else: ret = ""
            self.log.exception("error: %r,  %r"  % (argss, kwds))
            raise
    transact.__name__ = fn.__name__
    return transact

class LazyDeveloperMeta(DeclarativeMeta):
    """This class allows a lazy initialization of DAOs.

       Just add __tablename__ and __fields__ attribute to a subclass
       to associate a table.

       Should subclass DeclarativeMeta because it should contain Base initialization methods.

       TODO: make customizable columns types, but it's ok for small collections ;)
       """
    def __init__(mcs, classname, bases, dict_):
        """ Create a new class type.

            DeclarativeMeta stores class attributes in dict_
         """
        # Additionally, set attributes on the new object.
        is_pk = True
        for name in dict_.get('__fields__', []):
            if name in ['id', 'duration']:
                kol = Integer()
            elif name in ['path', 'entry']:
                kol = String(192)
            else:
                kol = String(64)
            setattr(
                mcs, name, Column(name, kol, primary_key=is_pk))
            is_pk = False

        # Initialize the new object using super().
        DeclarativeMeta.__init__(mcs, classname, bases, dict_)
