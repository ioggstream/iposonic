#cal path for loading _mysqlembedded
import sys, logging, os

sys.path.insert(0, './lib')
try:
    assert False
    import _mysqlembedded
    sys.modules['_mysql'] = _mysqlembedded
except (ImportError, AssertionError):
    #Fall back to mysql server module
    import _mysql

from sqlalchemy.exc import OperationalError

from datamanager.utils import synchronized
from datamanager.sqlite import SqliteIposonicDB, Base

class MySQLIposonicDB(SqliteIposonicDB):
    """MySQL standard and embedded version.

        Classic version requires uri, otherwise
        you need to play with embedded.
    """
    # mysql embedded
    #import _mysqlembedded as _mysql
    import _mysql

    log = logging.getLogger('MySQLIposonicDB')
    engine_s = "mysql+mysqldb"
    driver = _mysql

    #@synchronized(SqliteIposonicDB.sql_lock)
    def end_db(self):
        """MySQL requires teardown of connections and memory structures."""
        if self.initialized and self.driver:
            self.driver.server_end()

    @synchronized(SqliteIposonicDB.sql_lock)
    def init_db(self):
        """This method don't use @transactional, but instantiates its own connection."""
        if self.initialized:
            self.log.info("already initialized: %r" % self.datadir)
            return
        self.log.info("initializing database in %r" % self.datadir)
        if not os.path.isdir(self.datadir):
            os.mkdir(self.datadir)
            self.log.info("datadir created: %r" % self.datadir)
        self.driver.server_init(
            ['ipython', "--no-defaults", "-h", self.datadir, '--bootstrap', '--character-set-server', 'utf8'], 
            ['ipython_CLIENT', 'ipython_SERVER', 'embedded']
            )

        self.log.info("creating connection")
        conn = self.driver.connection(user=self.user, passwd=self.passwd)
        try:
            self.log.debug("set autocommit == True")
            conn.autocommit(True)
            
            if self.recreate_db:
                self.log.info("drop database")
                #conn.query("drop database %s;" % self.dbfile)
                conn.query("drop database if exists %s ;" % self.dbfile)
                conn.store_result()
    
            self.log.info("eventually create database %r" % self.dbfile)
            conn.query("create database if not exists %s ;" % self.dbfile)
            conn.store_result()

            conn.query("use %s;" % self.dbfile)
            conn.store_result()

            self.log.info("eventually create table iposonic")
            conn.query("create table if not exists iposonic(version text);")
            conn.store_result()
            
            conn.query("insert into iposonic(version) values('0.0.1');")
            conn.store_result()
            assert not conn.error()
        except OperationalError:
            self.log.exception("Error in connection")
        finally:
            self.log.info("Closing connection")
            conn.close()
        if self.recreate_db:
            self.log.info("%r.__init__ recreates db" % self.__class__)
            Base.metadata.create_all(self.engine)
        self.initialized = True
        #_mysql.server_end()
