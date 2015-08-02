#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc,xbmcgui
import pyxbmct.addonwindow as pyxbmct
sys.path.append(os.path.join(xbmc.translatePath( "special://home/addons/script.module.pyxbmctmanager/" ), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
from common import *
from database import *
from vfs import VFSClass
vfs = VFSClass()
DB_FILE = vfs.join(DATA_PATH, 'cache.db')
DB=SQLiteDatabase(DB_FILE)
ACTION_ENTER = 13 # What is this code?
ACTION_SELECT_ITEM = 7

def add_to_queue():
	SQL = "INSERT INTO queue(video_type, filename, raw_url, url) VALUES(?,?,?,?)"
	DB.execute(SQL, [args['video_type'], args['filename'], args['raw_url'], args['resolved_url']])
	DB.commit()

def view_queue():
	from pyxbmctmanager.window import Window
	class statusWindow(Window):
		def __init__(self, title):
			super(self.__class__,self).__init__(title,width=400, height=250, columns=3, rows=5)
			self.draw()
		def set_info_controls(self):
			
			def pg():
				pDialog = xbmcgui.DialogProgress()
				pDialog.create('Caching Progress')
				while True:
					pDialog.update(33, 'name', 'status')
					if (pDialog.iscanceled()):
						return
					xbmc.sleep(1000)
			
			self.add_label(self.create_label("Name:"), 0,0)
			self.add_label(self.create_label("Type:"), 1,0)
			self.add_label(self.create_label("Status:"), 2,0)
			
			self.create_button('close', 'Close')
			self.add_object('close', 4, 2)
			self.set_object_event('action', 'close', self.close)
			
			self.create_button('progress', 'Progress')
			self.add_object('progress', 4, 1)
			self.set_object_event('action', 'progress', pg)
			
			self.create_button('abort', 'Abort')
			self.add_object('abort', 4, 0)

			self.set_object_event('left', 'close', 'progress')
			self.set_object_event('left', 'progress', 'abort')
			self.set_object_event('right', 'abort', 'progress')
			self.set_object_event('right', 'progress', 'close')
	
	class QueueWindow(Window):
		def __init__(self, title):
			super(self.__class__,self).__init__(title,width=1000, height=650, columns=4, rows=18)
			self.draw()
		
		def show_menu(self):
			self.get_object('queue').getSelectedPosition()
			status = statusWindow('Status')
			status.set_object_event("focus", "close")
			status.show()
			
			
		def set_info_controls(self):
			self.create_list('queue', selectedColor=10, columnspan=4)
			self.add_object('queue', 1, 0, 6, 4)
			#self.connectEventList([pyxbmct.ACTION_MOUSE_LEFT_CLICK, ACTION_ENTER, ACTION_SELECT_ITEM],self.show_menu)

			items = []
			rows = DB.query("SELECT video_type, filename FROM queue WHERE status=1", force_double_array=True)
			self.__items = rows
			for r in rows: 
				items.append("%s. %s" % (rows.index(r)+1, r[1]))
			self.add_list_items('queue', items)
			
			self.set_object_event("action", "queue", self.show_menu)
			self.set_object_event("focus", "queue")
	queue = QueueWindow('%s Version: %s' % (ADDON_NAME, VERSION))
	queue.set_object_event("focus", "queue")
	queue.show()
	
	
args = ADDON.parse_query(sys.argv[2])
print args
if args['mode'] == 		'main':
	view_queue()
elif args['mode'] ==	'add_to_queue':
	add_to_queue()	