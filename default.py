#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
sys.path.append(os.path.join(xbmc.translatePath( "special://home/addons/script.module.pyxbmctmanager/" ), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
from common import *
from database import *
from vfs import VFSClass
vfs = VFSClass()
DB_FILE = vfs.join(DATA_PATH, 'cache.db')
DB=SQLiteDatabase(DB_FILE)


def add_to_queue():
	SQL = "INSERT INTO queue(video_type, filename, raw_url, url) VALUES(?,?,?,?)"
	DB.execute(SQL, [args['video_type'], args['filename'], args['raw_url'], args['resolved_url']])
	DB.commit()

def view_queue():
	from pyxbmctmanager.window import Window
	class QueueWindow(Window):
		def __init__(self, title):
			super(self.__class__,self).__init__(title,width=1000, height=650, columns=4, rows=10)
			self.draw()
			
		def set_info_controls(self):
			pass
	queue = QueueWindow('%s Version: %s' % (ADDON_NAME, VERSION))
	queue.show()
	
args = ADDON.parse_query(sys.argv[2])
print args
if args['mode'] == 		'main':
	view_queue()
elif args['mode'] ==	'add_to_queue':
	add_to_queue()	