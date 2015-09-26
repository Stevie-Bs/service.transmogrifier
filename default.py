#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import math
import xbmc,xbmcgui
from dudehere.routines import *
from dudehere.routines.window import Window
from dudehere.routines.vfs import VFSClass
vfs = VFSClass()

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

	class QueueWindow(Window):
		def __init__(self, title):
			super(self.__class__,self).__init__(title,width=800, height=500, columns=5, rows=10)
			self.draw()
		
		def set_info_controls(self):
			label = self.create_label("File:")
			self.add_label(label, 0, 0, pad_x=15, pad_y=10)
			
			self.filename = self.create_label("")
			self.add_label(self.filename, 0, 1, pad_x=15, pad_y=10)
			
			label = self.create_label("Status:")			
			self.add_label(label, 1, 0, pad_x=15, pad_y=10)
			
			self.status = self.create_label("")
			self.add_label(self.status, 1, 1, pad_x=15, pad_y=10)
			
			label = self.create_label("Progress:")
			self.add_label(label, 2, 0, pad_x=15, pad_y=10)
			
			label = self.create_label("Size:")
			self.add_label(label, 0, 3, pad_x=15, pad_y=10)
			
			self.size = self.create_label("")
			self.add_label(self.size, 0, 4, pad_x=15, pad_y=10)
			
			label = self.create_label("Priority:")
			self.add_label(label, 1, 3, pad_x=15, pad_y=10)
			
			self.priority = self.create_label("")
			self.add_label(self.priority, 1, 4, pad_x=15, pad_y=10)
			
			self.create_progress_bar('progress')
			self.add_object('progress', 2, 1, columnspan=4, pad_y=14)
			
			queue = [
					["tvshow 1", "tvshow", "tvshow1.avi", 1, 42, '512 mb'],
					["tvshow 2", "tvshow", "tvshow2.avi", 0, 0, '546 mb'],
					["tvshow 3", "tvshow", "tvshow3.avi", 0, 0, '546 mb'],
					["movie 1", "movie", "movie1.avi", 0, 0, '1516 mb'],
			]
			
			def show_status():
				print "ok"
				obj = self.getFocus()
				index = int(obj.getSelectedItem().getProperty('index'))
				self.priority.setLabel(str(index+1))
				self.filename.setLabel(queue[index][2])
				self.size.setLabel(queue[index][5])
				if queue[index][3] == 1:
					status = 'active'
					percent = float(queue[index][4]) / 100
					self.update_progress_bar('progress', percent, '1.4 MB/s')
				else:
					self.update_progress_bar('progress', 0, '')
					status = 'pending'
				self.status.setLabel(status)	
				
				
			
			items = [item[0] for item in queue]
			self.create_list('queue')
			self.add_object('queue', 3,1,7,4)
			self.add_list_items('queue', items, selectable=False, call_back=show_status)
			icon_root = vfs.join(ROOT_PATH, 'resources/www/html/images')
			for item in queue:
				index = queue.index(item)
				icon = vfs.join(icon_root, item[1] + '.png')
				self.get_object('queue').getListItem(index).setIconImage(icon)
			
			'''import platform
			hostname = platform.node()
			address = '[B][COLOR blue]http://%s:%s[/COLOR][/B]' % (hostname, ADDON.get_setting('control_port'))
			self.add_label(self.create_label("This is not yet implemented.", alignment=2, font="font14"), 0,0,columnspan=3)
			self.add_label(self.create_label("Go to the web service address for management.", alignment=2), 1,0,columnspan=3)
			self.add_label(self.create_label(address, alignment=2), 2,0,columnspan=3)
			
			'''
			
			self.create_button('close', 'Close')
			self.add_object("close", 9, 2)
			self.set_object_event('action', 'close', self.close)
			
	queue = QueueWindow('%s Version: %s' % (ADDON_NAME, VERSION))
	queue.set_object_event("focus", "close")
	queue.show()

	
args = ADDON.parse_query(sys.argv[2])
print args
if args['mode'] == 		'main':
	view_queue()