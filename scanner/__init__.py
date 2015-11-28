"""Scan media collection with inotify"""
# -*- encode: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import logging
from os.path import join, basename

#from decorator import decorator
#from pyinotify import ProcessEvent, WatchManager, IN_DELETE, IN_CREATE, ThreadedNotifier
from mediamanager.stringutils import to_unicode
from Queue import Queue
from mediamanager import stringutils, MediaManager

q = Queue()

logging.basicConfig(level=logging.WARN)

log = logging.getLogger(__name__)


def add_or_log(path, album=False, iposonic=None):
    try:
        iposonic.add_path(path, album)
    except Exception as e:
        iposonic.log.exception("Errore generico in add_or_log")



#class ProcessDir(ProcessEvent):
#    """Performs Actions based on mask values.
#
#        event functions signature should be
#            event_f(self, event)
#        every other argument should be passed via `self`
#
#        inotify returns an event object!
#    """
#    def __init__(self, iposonic):
#        self.iposonic = iposonic
#
#    #@decorator
#    def unbreakable(fn):
#        def f(self, *args, **kwds):
#            try:
#                log.info("executing unbreakable %s" % f.__name__)
#                fn(self, *args, **kwds)
#            except Exception:
#                log.exception("error managing %s" % f.__name__)
#        return f
#
#    @unbreakable
#    def process_IN_CREATE(self, event):
#        log.info("Creating File and File Record:", event.pathname)
#        log.info("event object: %s" % {'path': event.path, 'name': event.name})
#        #self.iposonic.add_path(event.pathname)
#
#    @unbreakable
#    def process_IN_DELETE(self, event):
#        log.info("Deleting File and File Record:", event.pathname)
#        log.debug("event object: %s" % event)
#        self.iposonic.delete_entry(event.pathname)
#

def eventually_rename_child(child, dir_path, rename_non_utf8=True):
    #
    # To manage non-utf8 filenames
    # the easiest thing is to rename
    # paths in utf.
    #
    # This may cause issues for collections
    # stored on windows or vfat filesystem.
    #
    # This is the KISS-siest approach
    # that avoids continuously encode
    # and decode of the filenames.
    #
    if not isinstance(child, unicode):
        if not rename_non_utf8:
            log.warn(
                "skipping non unicode path: %r " % child)
            raise ValueError("Unsupported non utf-8 encoding")
        # guess the right encoding
        # then preserve the encoded string
        # while changing encoding
        log.info("renaming child...%r", child)
        child_new = to_unicode(child)
#        os.rename(
#            b'%s/%s' % (dir_path.encode('utf-8'), child),
#            b'%s/%s' % (
#                dir_path.encode('utf-8'), child_new.encode('utf-8'))
#        )
        try:
            src = b'%s/%s' % (dir_path.encode('utf-8'), bytes(child))
            dst = b'%s/%s' % (dir_path.encode('utf-8'), child_new.encode('utf-8'))
            os.rename(src, dst)
        except:
            log.exception("Unicode Error with %r %r %r" % (dir_path, type(dir_path), dir_path.encode('utf-8')))
            raise UnicodeDecodeError
        child = child_new
    return child


def walk_music_folder(iposonic_app, forever=True):
    # Filesystem wolking should be moved to bytes instead
    #   of unicode
    log.info("Start walker thread")

    def add_or_log(path, album=False):
        try:
            iposonic_app.add_path(path, album)
        except Exception as e:
            iposonic_app.log.exception("Generic error")

    for music_folder in iposonic_app.get_music_folders():
        log.info("Walking into: %r" % music_folder)
        # Assume artist names in utf-8
        artists_local = [x for x in os.listdir(
            music_folder) if os.path.isdir(join("/", music_folder, x))]
        log.info("Local artists: %r" % artists_local)
        #index all artists
        for a in artists_local:
            try:
                iposonic_app.log.info("scanning artist: %s" % repr(a))
            except:
                iposonic_app.log.warn(u'cannot read object: %s' % repr(a))
            if a:
                try:
                    a = eventually_rename_child(a, music_folder)
                except:
                    log.exception("error adding %r" % a)
                    continue
                path = join("/", music_folder, a)
                add_or_log(path)

                #
                # Scan recurrently only if not refresh_always
                #
                dirpath, dirnames, filenames = None, None, None
                try:
                    for dirpath, dirnames, filenames in os.walk(path.encode('utf-8')):
                        # note: as path is encoded, dirpath, dirnames and filenames are bytes
                        #       and not unicode
                        for d in dirnames:
                            try:
                                # d = eventually_rename_child(d, dirpath)
                                d = join(b"/", path.encode('utf-8'), dirpath, d).decode('utf-8')
                                add_or_log(d, album=True)
                            except:
                                iposonic_app.log.exception("error: %s, %s, %s" % (repr(path), repr(dirpath), repr(d)))
                                #iposonic_app.log.info("error: %s, %s, %s" % stringutils.to_unicode(d))

                        for f in filenames:
                            try:
                                #if not any([ x for x in MediaManager.ALLOWED_FILE_EXTENSIONS if f[:-4].lower().endswith(x) ]):
                                if not f[:-4].decode('utf-8','ignore').lower().endswith(tuple(MediaManager.ALLOWED_FILE_EXTENSIONS)):
                                    continue
                                #p = join("/", path.encode('utf-8'), dirpath.encode('utf-8'), f.encode('utf-8')).decode('utf-8')
                                p = join("/", path, dirpath, f)
                                iposonic_app.log.info("p: %s" % repr(p))
                                add_or_log(p)
                            except UnicodeDecodeError as e:
                                iposonic_app.log.warn("bad file name: %r" % f)
                            except Exception as e:
                                iposonic_app.log.exception("error: %r" % f)
                except:
                    iposonic_app.log.exception("error traversing: %s: %s %s %s" % (repr(path), repr(dirpath), repr(dirnames), repr(filenames)))
                finally:
                    iposonic_app.log.info("finish traversing: %r" % path)

    # do something when the app signals something
    while forever:
        item = q.get()
        log.exception("Do something with that messages: %r" % item)
        q.task_done()


def watch_music_folder(iposonic_app):
    #Pyionotify
    wm = WatchManager()
    mask = IN_DELETE | IN_CREATE
    notifier = ThreadedNotifier(wm, ProcessDir(iposonic_app))
    notifier.start()
    for path in iposonic_app.get_music_folders():
        iposonic_app.log.info("watching path: %s" % path)
        try:
            wdd = wm.add_watch(path.encode('utf-8'), mask, rec=True)
        except Exception as e:
            iposonic_app.log.exception("error in watch thread: %r" % path)
