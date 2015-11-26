import xbmc
from dudehere.routines import *
if ADDON.get_setting('database_type')=='1':
	from dudehere.routines.database import MySQLDatabase as DatabaseAPI
	class MyDatabaseAPI(DatabaseAPI):
		def _initialize(self):
			SQL = '''CREATE TABLE IF NOT EXISTS`queue` (
					`id` int(11) NOT NULL AUTO_INCREMENT,
					`priority` int(11) NOT NULL DEFAULT '10',
					`video_type` varchar(10) DEFAULT NULL,
					`filename` varchar(150) NOT NULL,
					`imdb_id` varchar(15) DEFAULT NULL,
					`season` tinyint(3) DEFAULT NULL,
					`episode` tinyint(3) DEFAULT NULL,
					`title` varchar(225) DEFAULT NULL,
					`fileid` varchar(75) DEFAULT NULL,
					`raw_url` varchar(225) DEFAULT NULL,
					`url` varchar(225) DEFAULT NULL,
					`save_dir` varchar(225) DEFAULT NULL,
					`source_addon` varchar(225) DEFAULT NULL,
					`status` tinyint(4) NOT NULL DEFAULT '1',
					PRIMARY KEY (`id`)
					) ENGINE=InnoDB;
			'''
			ADDON.log(SQL)
			self.execute(SQL)
			self.commit()
			ADDON.set_setting('database_mysql_init', 'true')
			ADDON.set_setting(self.version_flag, str(self.db_version))
	DB_NAME = ADDON.get_setting('database_mysql_name')
	DB_USER = ADDON.get_setting('database_mysql_user')
	DB_PASS = ADDON.get_setting('database_mysql_pass')
	DB_PORT = ADDON.get_setting('database_mysql_port')
	DB_ADDRESS = ADDON.get_setting('database_mysql_host')
	DB_TYPE = 'mysql'
	DB=MyDatabaseAPI(DB_ADDRESS, DB_NAME, DB_USER, DB_PASS, DB_PORT, connect=False, version=1, quiet=True, check_version=True)
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
					"source_addon" TEXT,
					"status" INTEGER DEFAULT (1)
					)
			'''
			ADDON.log(SQL)
			self.execute(SQL)
			self.commit()
			ADDON.set_setting('database_sqlite_init', 'true')
			ADDON.set_setting(self.version_flag, str(self.db_version))
	DB_TYPE = 'sqlite'
	DB_FILE = xbmc.translatePath(ADDON.get_setting('database_sqlite_file'))
	DB=MyDatabaseAPI(DB_FILE, connect=False, quiet=True, version=1, check_version=True)