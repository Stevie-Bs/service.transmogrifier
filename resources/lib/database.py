import sys,os,re
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
from common import *
IGNORE_UNIQUE_ERRORS = True

class DatabaseClass:
	def __init__(self, quiet=True):
		self.quiet=quiet
		self._unique_str = 'column (.)+ is not unique$'

	def commit(self):
		ADDON.log("Commiting to %s" % self.db_file)
		self.DBH.commit()

	def disconnect(self):
		if self.db_type == 'sqlite':
			print "Disconnecting from %s" % self.db_file
			self.DBC.close()
		else:
			print "Disconnecting from %s on %s" % (self.dbname, self.host)
			self.DBC.close()

	def query(self, SQL, data=None, force_double_array=False):
		if data:
			self.DBC.execute(SQL, data)
		else:
			self.DBC.execute(SQL)
		rows = self.DBC.fetchall()
		if(len(rows)==1 and not force_double_array):
			return rows[0]
		else:
			return rows

	def execute(self, SQL, data=[]):
		try:
			if data:
				self.DBC.execute(SQL, data)
			else:
				self.DBC.execute(SQL)
			try:
				self.lastrowid = self.DBC.lastrowid
			except:
				self.lastrowid = None
		except Exception, e:
			if IGNORE_UNIQUE_ERRORS and re.match(self._unique_str, str(e)):				
				ADDON.log('****** SQL ERROR: %s' % e)
	
	def execute_many(self, SQL, data):
		try:
			self.DBC.executemany(SQL, data)
		except Exception, e:
			if IGNORE_UNIQUE_ERRORS and re.match(self._unique_str, str(e)):				
				print '****** SQL ERROR: %s' % e			

class SQLiteDatabase(DatabaseClass):
	def __init__(self, db_file='', quiet=False):
		self.quiet=quiet
		self._unique_str = 'column (.)+ is not unique$'
		self.db_type = 'sqlite'
		self.lastrowid = None
		self.db_file = db_file		
		self._connect()
	
	def _initialize(self):
		self.execute('CREATE TABLE IF NOT EXISTS "queue" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "priority" INTEGER DEFAULT (10), "video_type" TEXT, "filename" TEXT, "uuid" TEXT, "raw_url" TEXT, "url" TEXT, "status" INTEGER DEFAULT (1))')
		self.commit()
		ADDON.addon.setSetting('database_init', 'true')	

	def close(self):
		self.DBH.close()

	def _connect(self):
		global ADDON
		if not self.quiet:
			ADDON.log("Connecting to %s" % self.db_file)
		try:
			from sqlite3 import dbapi2 as database
			if not self.quiet:
				ADDON.log("Loading sqlite3 as DB engine")
		except:
			from pysqlite2 import dbapi2 as database
			if not self.quiet:
				ADDON.log("Loading pysqlite2 as DB engine")
		if not self.quiet:
			ADDON.log("Connecting to SQLite on: %s" % self.db_file)
		self.DBH = database.connect(self.db_file)
		self.DBC = self.DBH.cursor()
		
		if ADDON.get_setting('database_init') != 'true':
			self._initialize()