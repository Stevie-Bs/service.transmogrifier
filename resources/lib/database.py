import xbmc
from dudehere.routines import *
if ADDON.get_setting('database_mysql')=='true':
	from dudehere.routines.database import MySQLDatabase as DatabaseAPI
	class MyDatabaseAPI(DatabaseAPI):
		def _initialize(self):
			SQL = '''CREATE TABLE IF NOT EXISTS `queue` (
					"id" INTEGER PRIMARY KEY AUTOINCREMENT, 
					"priority" INTEGER DEFAULT (10), 
					"video_type" TEXT, 
					"filename" TEXT,
					"imdb_id" TEXT,
					"season" INTEGER,
					"episode" INTEGER,
					"title" TEXT,
					"fileid" TEXT, 
					"raw_url" TEXT, 
					"url" TEXT, 
					"save_dir" TEXT,
					"status" INTEGER DEFAULT (1)
					)'''
			self.execute(SQL)
			self.commit()
			ADDON.addon.setSetting('database_init_mysql', 'true')
	DB_NAME = ADDON.get_setting('database_mysql_name')
	DB_USER = ADDON.get_setting('database_mysql_user')
	DB_PASS = ADDON.get_setting('database_mysql_pass')
	DB_PORT = ADDON.get_setting('database_mysql_port')
	DB_ADDRESS = ADDON.get_setting('database_mysql_host')
	DB_TYPE = 'mysql'
	DB=MyDatabaseAPI(DB_ADDRESS, DB_NAME, DB_USER, DB_PASS, DB_PORT)
else:
	from dudehere.routines.database import SQLiteDatabase as DatabaseAPI	
	class MyDatabaseAPI(DatabaseAPI):
		def _initialize(self):
			SQL = '''CREATE TABLE IF NOT EXISTS "queue" (
					"id" INTEGER PRIMARY KEY AUTOINCREMENT, 
					"priority" INTEGER DEFAULT (10), 
					"video_type" TEXT, 
					"filename" TEXT,
					"imdb_id" TEXT,
					"season" INTEGER,
					"episode" INTEGER,
					"title" TEXT,
					"fileid" TEXT, 
					"raw_url" TEXT, 
					"url" TEXT, 
					"save_dir" TEXT,
					"status" INTEGER DEFAULT (1)
					)'''
			self.execute(SQL)
			self.commit()
			ADDON.addon.setSetting('database_init_sqlite', 'true')
	DB_TYPE = 'sqlite'
	DB_FILE = xbmc.translatePath(ADDON.get_setting('database_sqlite_file'))
	DB=MyDatabaseAPI(DB_FILE)