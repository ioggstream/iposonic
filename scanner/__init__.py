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
from mediamanager import stringutils

q = Queue()

logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)


def add_or_log(path, album=False, iposonic=None):
    try:
        iposonic.add_path(path, album)
    except Exception as e:
        iposonic.log.error(e)



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
    print ("eventually_rename_child")
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
                "skipping non unicode path: %s " % to_unicode(child))
            raise ValueError("Unsupported non utf-8 encoding")
        # guess the right encoding
        # then preserve the encoded string
        # while changing encoding
        child_new = to_unicode(child)
        os.rename(
            b'%s/%s' % (dir_path.encode('utf-8'), child),
            b'%s/%s' % (
                dir_path.encode('utf-8'), child_new.encode('utf-8'))
        )
        child = child_new
    return child


def walk_music_folder(iposonic):
    log.info("Start walker thread")

    def add_or_log(path, album=False):
        try:
            iposonic.add_path(path, album)
        except Exception as e:
            iposonic.log.error(e)

    for music_folder in iposonic.get_music_folders():
        log.info("Walking into: %s" % music_folder)
        # Assume artist names in utf-8
        artists_local = [x for x in os.listdir(
            music_folder) if os.path.isdir(join("/", music_folder, x))]
        log.info("Local artists: %s" % artists_local)
        #index all artists
        for a in artists_local:
            try:
                iposonic.log.info(u"scanning artist: %s" % a)
            except:
                iposonic.log.info(u'cannot read object: %s' % a.__class__)
            if a:
                a = eventually_rename_child(a, music_folder)
                path = join("/", music_folder, a)
                add_or_log(path)

                #
                # Scan recurrently only if not refresh_always
                #
                try:
                    for dirpath, dirnames, filenames in os.walk(path):
                        for d in dirnames:
                            try:
                                d = eventually_rename_child(d, dirpath)
                                d = join("/", path, dirpath, d)
                                add_or_log(d, album=True)
                            except:
                                iposonic.log.info("error: %s" % stringutils.to_unicode(d))

                        for f in filenames:
                            try:
                                p = join("/", path.encode('utf-8'), dirpath.encode('utf-8'), f.encode('utf-8')).decode('utf-8')
                                iposonic.log.info("p: %s" % stringutils.to_unicode(p))
                                add_or_log(p)
                            except:
                                iposonic.log.info("error: %s" % stringutils.to_unicode(f))
                except:
                    iposonic.log.warn("error traversing: %s" % path)

    # do something when the app signals something
    while True:
        item = q.get()
        log.exception("Do something with that messages: %s" % item)
        q.task_done()


def watch_music_folder(iposonic):
    #Pyionotify
    wm = WatchManager()
    mask = IN_DELETE | IN_CREATE
    notifier = ThreadedNotifier(wm, ProcessDir(iposonic))
    notifier.start()
    for path in iposonic.get_music_folders():
        log.info("watching path: %s" % path)
        try:
            wdd = wm.add_watch(path.encode('utf-8'), mask, rec=True)
        except Exception as e:
            log.exception("error in watch thread: %s" % path)
