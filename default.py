#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import math
import xbmc,xbmcgui
import socket
import pyxbmct.addonwindow as pyxbmct
sys.path.append(os.path.join(xbmc.translatePath( "special://home/addons/script.module.pyxbmctmanager/" ), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
from dudehere.routines import *
from dudehere.routines.vfs import VFSClass
vfs = VFSClass()
if not vfs.exists(DATA_PATH): vfs.mkdir(DATA_PATH)
if ADDON.get_setting('database_mysql')=='true':
	from dudehere.routines.database import MySQLDatabase as DatabaseAPI
	class MyDatabaseAPI(DatabaseAPI):
		def _initialize(self):
			SQL = '''CREATE TABLE IF NOT EXISTS `queue` (
					`id` INT NOT NULL AUTO_INCREMENT, 
					`video_type` VARCHAR(10) NULL, 
					`priority` INT NULL DEFAULT 10, 
					`filename` VARCHAR(150) NOT NULL, 
					`uuid` VARCHAR(45) NULL, 
					`raw_url` VARCHAR(225) NULL, 
					`url` VARCHAR(225) NULL, 
					`status` TINYINT NULL, 
					PRIMARY KEY (`id`)
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
					"uuid" TEXT, 
					"raw_url" TEXT, 
					"url" TEXT, 
					"status" INTEGER DEFAULT (1)
					)'''
			self.execute(SQL)
			self.commit()
			ADDON.addon.setSetting('database_init_sqlite', 'true')
	DB_TYPE = 'sqlite'
	DB_FILE = xbmc.translatePath(ADDON.get_setting('database_sqlite_file'))
	DB=MyDatabaseAPI(DB_FILE)

WINDOW_PREFIX = 'transmogrifier'
MESSAGE_ACTION_OK = 110
MESSAGE_EXIT = 111
ACTION_ENTER = 13
ACTION_SELECT_ITEM = 7

def set_property( k, v):
		k = "%s.%s" % (WINDOW_PREFIX, k)
		xbmcgui.Window(10000).setProperty(k, str(v))
	
def get_property(k):
	k = "%s.%s" % (WINDOW_PREFIX, k)
	p = xbmcgui.Window(10000).getProperty(k)
	if p == 'false': return False
	if p == 'true': return True
	return p

def view_queue():
	from pyxbmctmanager.window import Window

	class QueueWindow(Window):
		def __init__(self, title):
			super(self.__class__,self).__init__(title,width=500, height=280, columns=3, rows=5)
			self.draw()
		
		def set_info_controls(self):
			address = '[B][COLOR blue]http://%s:%s[/COLOR][/B]' % (socket.gethostname(), ADDON.get_setting('control_port'))
			self.add_label(self.create_label("This is not yet implemented.", alignment=2, font="font14"), 0,0,columnspan=3)
			self.add_label(self.create_label("Go to the web service address for management.", alignment=2), 1,0,columnspan=3)
			self.add_label(self.create_label(address, alignment=2), 2,0,columnspan=3)
			
			self.create_button('close', 'Close')
			self.add_object("close", 4, 1)
			self.set_object_event('action', 'close', self.close)
		
		'''def confirm(self, msg='', msg2='', msg3=''):
			dialog = xbmcgui.Dialog()
			return dialog.yesno(msg, msg2, msg3)
		
		def show_menu(self):
			self._index = self.get_object('queue').getSelectedPosition()
			name = self.get_object('queue').getListItem(self._index).getProperty('original_label')
			
			if name == '':
				name = self.get_object('queue').getListItem(self._index).getLabel()
			self.nameLabel.setLabel(name)
			self.typeLabel.setLabel(self.__items[self._index][0])
			table = ["error", "pending", "caching", "complete"]
			self.statusLabel.setLabel(table[self.__items[self._index][3]])		
				
		def pg(self):
				pDialog = xbmcgui.DialogProgress()
				pDialog.create('Caching Progress')
				while True:
					pDialog.update(33, 'name', 'status')
					if (pDialog.iscanceled()):
						return
					xbmc.sleep(1000)	
		
		def set_progress(self, percent):
			if percent == '': percent = 0
			percent = int(math.floor(int(percent)/2))
			s = '[%s%s]' % (('=' * percent), ('--' * (50-percent)))
			self.progressLabel.setLabel(s)
		
		def re_queue(self):
			id = self.__items[self._index][2]
			name = self.__items[self._index][1]
			if not self.confirm("Update queue", "Restart in queue?", name): return
			DB.execute("UPDATE queue SET status=1 WHERE id=?", [id])
			DB.commit()
			self.close()
			queue = QueueWindow('%s Version: %s' % (ADDON_NAME, VERSION))
			queue.set_object_event("focus", "queue")
			queue.show()	
		
		def delete(self):
			id = self.__items[self._index][2]
			name = self.__items[self._index][1]
			if not self.confirm("Update queue", "Delete from queue?", name): return
			DB.execute("DELETE FROM queue WHERE id=?", [id])
			DB.commit()
			self.close()
			queue = QueueWindow('%s Version: %s' % (ADDON_NAME, VERSION))
			queue.set_object_event("focus", "queue")
			queue.show()	
			
		def abort(self):
			id = self.__items[self._index][2]
			name = self.__items[self._index][1]
			if not self.confirm("Update queue", "Abort Transmogrification?", name): return
			DB.execute("UPDATE queue SET status=0 WHERE id=?", [id])
			DB.commit()
			set_property('abort_all', 'true')
		
		def refresh(self):
			items = []
			rows = DB.query("SELECT video_type, filename, id, status FROM queue", force_double_array=True)
			self.__items = rows
			for r in rows: 
				items.append("%s. %s" % (rows.index(r)+1, r[1]))	
			self.add_list_items('queue', items)
			
		def set_info_controls(self):

			self.add_label(self.create_label("Name:"), 0,0)
			self.add_label(self.create_label("Type:"), 1,0)
			self.add_label(self.create_label("Status:"), 2,0)
			self.add_label(self.create_label("Progress:"), 3,0)
			self.nameLabel = self.create_label('')
			self.add_label(self.nameLabel, 0,1)
			self.typeLabel = self.create_label('')
			self.add_label(self.typeLabel, 1,1)
			self.statusLabel = self.create_label('')
			self.add_label(self.statusLabel, 2,1)
			
			self.progressLabel = self.create_label('')
			self.add_label(self.progressLabel, 3,1, columnspan=3)
			
			self.create_list('queue', columnspan=4)
			self.add_object('queue', 5, 0, 10, 4)
		
			items = []
			rows = DB.query("SELECT video_type, filename, id, status FROM queue", force_double_array=True)
			self.__items = rows
			for r in rows: 
				items.append("%s. %s" % (rows.index(r)+1, r[1]))
				
			self.add_list_items('queue', items)
			
			self.create_button('close', 'Close')
			self.add_object("close", 14, 0, rowspan=2)
			self.set_object_event('action', 'close', self.close)
			
			self.create_button('delete', 'Delete')
			self.add_object('delete', 14, 1, rowspan=2)
			
			self.create_button("abort", "Abort")
			self.add_object("abort", 14, 2, rowspan=2)
			
			self.create_button("restart", "Restart")
			self.add_object("restart", 14, 3, rowspan=2)
			
			self.set_object_event('left', 'restart', 'abort')
			self.set_object_event('left', 'abort', 'delete')
			self.set_object_event('left', 'delete', 'close')
			
			self.set_object_event('right', 'close', 'delete')
			self.set_object_event('right', 'delete', 'abort')
			self.set_object_event('right', 'abort', 'restart')
			
			self.set_object_event('up', 'close', 'queue')
			self.set_object_event('up', 'delete', 'queue')
			self.set_object_event('up', 'restart', 'queue')
			self.set_object_event('up', 'abort', 'queue')
			self.set_object_event('down', 'queue', 'close')
			
			self.set_object_event("action", "queue", self.show_menu)
			
			self.set_object_event("action", "restart", self.re_queue)
			self.set_object_event("action", "delete", self.delete)
			self.set_object_event("action", "abort", self.abort)
			
			self.set_object_event("focus", "queue")
		'''
			
	queue = QueueWindow('%s Version: %s' % (ADDON_NAME, VERSION))
	#queue.set_object_event("focus", "queue")
	queue.show()

	
args = ADDON.parse_query(sys.argv[2])
print args
if args['mode'] == 		'main':
	view_queue()