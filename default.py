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
			label = self.create_label("Status:")
			self.add_label(label, 1, 0, pad_x=15, pad_y=10)
			label = self.create_label("Progress:")
			self.add_label(label, 2, 0, pad_x=15, pad_y=10)
			
			label = self.create_label("Size:")
			self.add_label(label, 0, 3, pad_x=15, pad_y=10)
			
			label = self.create_label("Priority:")
			self.add_label(label, 1, 3, pad_x=15, pad_y=10)
			
			self.create_progress_bar('progress')
			self.add_object('progress', 2,1,columnspan=4, pad_y=14)
			
			items = ["file 1", "file 2"]
			self.create_list('queue')
			self.add_object('queue', 3,0,7,5)
			self.add_list_items('queue', items, 0, allow_multiple=False, allow_toggle=False)
			
			'''import platform
			hostname = platform.node()
			address = '[B][COLOR blue]http://%s:%s[/COLOR][/B]' % (hostname, ADDON.get_setting('control_port'))
			self.add_label(self.create_label("This is not yet implemented.", alignment=2, font="font14"), 0,0,columnspan=3)
			self.add_label(self.create_label("Go to the web service address for management.", alignment=2), 1,0,columnspan=3)
			self.add_label(self.create_label(address, alignment=2), 2,0,columnspan=3)
			
			'''
			
			self.create_button('close', 'Close')
			self.add_object("close", 9, 1)
			self.set_object_event('action', 'close', self.close)
			
	queue = QueueWindow('%s Version: %s' % (ADDON_NAME, VERSION))
	queue.set_object_event("focus", "close")
	queue.show()

	
args = ADDON.parse_query(sys.argv[2])
print args
if args['mode'] == 		'main':
	view_queue()