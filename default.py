#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import math
import xbmc,xbmcgui
from threading import Thread
from dudehere.routines import *
from dudehere.routines.window import Window
from dudehere.routines.transmogrifier import TransmogrifierAPI
from dudehere.routines.vfs import VFSClass
vfs = VFSClass()

WINDOW_PREFIX = 'transmogrifier'
MESSAGE_ACTION_OK = 110
MESSAGE_EXIT = 111
ACTION_ENTER = 13
ACTION_SELECT_ITEM = 7
ACTION_MOUSE_RIGHT_CLICK = 101
ACTION_SHOW_INFO = 11
ACTION_CONTEXT_MENU = 117
CONTEX_ACTION = None
STATUS = enum(PENDING=1, ACTIVE=2, COMPLETE=3, PAUSED=4, FAILED=-1)

def set_property( k, v):
		k = "%s.%s" % (WINDOW_PREFIX, k)
		xbmcgui.Window(10000).setProperty(k, str(v))
	
def get_property(k):
	k = "%s.%s" % (WINDOW_PREFIX, k)
	p = xbmcgui.Window(10000).getProperty(k)
	if p == 'false': return False
	if p == 'true': return True
	return p

def format_size(bytes):
	size = int(bytes) / (1024 * 1024)
	if size > 2000:
		size = size / 1024
		unit = 'GB'
	else :
		unit = 'MB'
	size = "%s %s" % (size, unit)
	return size
def view_queue():
	abort_poll = False
	TM = TransmogrifierAPI()
	class ContextWindow(Window):
		def __init__(self, title):
			super(self.__class__,self).__init__(title,width=350, height=180, columns=1, rows=3)
			self.items = []
			
		def event(self):
			global CONTEX_ACTION
			obj = self.getFocus()
			CONTEX_ACTION = obj.getSelectedItem().getLabel().lower()
			self.close()
		
		def set_info_controls(self):
			self.create_list('dialog')
			self.add_object('dialog', 0,0,5,1)
			self.add_list_items('dialog', self.items, selectable=False, call_back=self.event)
			icon_root = vfs.join(ROOT_PATH, 'resources/www/html/images')
			for item in self.items:
				index = self.items.index(item)
				icon = vfs.join(icon_root, item.lower() + '.png')
				print icon
				self.get_object('dialog').getListItem(index).setIconImage(icon)
			self.set_object_event('focus', 'dialog')
			
	class QueueWindow(Window):
		def __init__(self, title):
			super(self.__class__,self).__init__(title,width=800, height=500, columns=5, rows=10)
			self.draw()	
		
		def set_info_controls(self):
			connection = "[COLOR blue]http://%s:%s[/COLOR]"
			if ADDON.get_setting('connect_remote') == 'true':
				connection = connection % (ADDON.get_setting('remote_host'), ADDON.get_setting('remote_control_port'))
			else:
				connection = connection % ('localhost', ADDON.get_setting('control_port'))
			label = self.create_label(connection)
			self.add_label(label, 9, 0, pad_x=15, pad_y=7, columnspan=3)
			
			label = self.create_label("File:")
			self.add_label(label, 0, 0, pad_x=15, pad_y=10)
			
			self.filename = self.create_label("")
			self.add_label(self.filename, 0, 1, pad_x=15, pad_y=10)
			
			label = self.create_label("Status:")			
			self.add_label(label, 1, 0, pad_x=15, pad_y=5)
			
			self.status = self.create_label("")
			self.add_label(self.status, 1, 1, pad_x=15, pad_y=5)
			
			label = self.create_label("Progress:")
			self.add_label(label, 2, 0, pad_x=15, pad_y=10)
			
			label = self.create_label("Size:")
			self.add_label(label, 0, 3, pad_x=15, pad_y=10)
			
			self.size = self.create_label("")
			self.add_label(self.size, 0, 4, pad_x=15, pad_y=10)
			
			label = self.create_label("Priority:")
			self.add_label(label, 1, 3, pad_x=15, pad_y=5)
			
			self.priority = self.create_label("")
			self.add_label(self.priority, 1, 4, pad_x=15, pad_y=5)
			
			self.create_progress_bar('progress')
			self.add_object('progress', 2, 1, columnspan=4, pad_y=14)
			
			queue = TM.get_queue()
			self.queue_data = queue['queue']
			queue = queue['queue']
			
			def show_status():
				obj = self.getFocus()
				for index in xrange(obj.size()):
					if index == int(obj.getSelectedItem().getProperty('index')):
						if obj.getListItem(index).getLabel2() == '':
							obj.getListItem(index).setLabel2(obj.getListItem(index).getLabel())
							obj.getListItem(index).setLabel('[B][COLOR yellow]' + obj.getListItem(index).getLabel2() + '[/COLOR][/B]')
					else:
						if obj.getListItem(index).getLabel2() != '':	
							obj.getListItem(index).setLabel(obj.getListItem(index).getLabel2())
							obj.getListItem(index).setLabel2('')
							
				index = int(obj.getSelectedItem().getProperty('index'))
				self.priority.setLabel('')
				self.filename.setLabel(queue[index][2])
				
				if queue[index][3] == STATUS.PENDING:
					status = 'pending'
					self.priority.setLabel(str(queue[index][6]))
				elif queue[index][3] == STATUS.ACTIVE:
					status = 'active'
					
					self.file_id = queue[index][5]
					self.id = queue[index][0]
				elif queue[index][3] == STATUS.COMPLETE:
					status = 'complete'
				elif queue[index][3] == STATUS.PAUSED:
					status = 'paused'
				else:
					status = 'failed'
				self.status.setLabel(status)	
				
			def show_context():
				try:
					global CONTEX_ACTION
					obj = self.getFocus()
					index = int(obj.getSelectedItem().getProperty('index'))
					if obj.getSelectedItem().getLabel2() == '': 
						obj.getSelectedItem().setLabel2(obj.getSelectedItem().getLabel())
						obj.getSelectedItem().setLabel('[B][COLOR yellow]' + obj.getSelectedItem().getLabel2() + '[/COLOR][/B]')
					CONTEX_ACTION = None
					context = ContextWindow(queue[index][2])
					if queue[index][3] == STATUS.PENDING:
						context.items = ["Remove", "Priority Up", "Priority Down"]
					elif queue[index][3] == STATUS.ACTIVE:
						context.items = ["Abort"]
					elif queue[index][3] == STATUS.COMPLETE:
						context.items = ["Requeue", "Remove"]
					elif queue[index][3] == STATUS.PAUSED:
						context.items = ["Requeue", "Remove", "Resume"]
					else:
						context.items = ["Requeue", "Remove"]
					context.show()
					obj.getSelectedItem().setLabel(obj.getSelectedItem().getLabel2())
					obj.getSelectedItem().setLabel2('')
					print CONTEX_ACTION
					if CONTEX_ACTION=='requeue':
						print self.queue_data[index]
						self.status.setLabel('pending')
						#self.queue_data[index][3] = 1
						print TM.restart(self.queue_data[index][0])
						self.queue_data = TM.get_queue()['queue']
					elif CONTEX_ACTION=='abort':
						print TM.abort(self.queue_data[index][5])
						self.status.setLabel('failed')
						self.queue_data = TM.get_queue()['queue']
					elif CONTEX_ACTION=='remove':
						TM.delete(self.queue_data[index][0])
						self.status.setLabel('')
						#del self.queue_data[index]
						self.queue_data = TM.get_queue()['queue']
						obj.removeItem(index)
				except: pass
			
			items = ["%s - %s" % (item[7], item[2]) for item in queue]
			self.create_list('queue')
			self.add_object('queue', 3,0,7,5)
			self.add_list_items('queue', items, selectable=False, call_back=show_status)
			icon_root = vfs.join(ROOT_PATH, 'resources/www/html/images')
			for item in queue:
				index = queue.index(item)
				icon = vfs.join(icon_root, item[1] + '.png')
				self.get_object('queue').getListItem(index).setIconImage(icon)
			
			self.connectEventList([ACTION_MOUSE_RIGHT_CLICK,ACTION_SHOW_INFO, ACTION_CONTEXT_MENU], show_context)
			
			self.create_button('close', 'Close')
			self.add_object("close", 9, 4)
			self.create_button('settings', 'Settings')
			self.add_object("settings", 9, 3)
			self.set_object_event('action', 'settings', ADDON.addon.openSettings)
			self.set_object_event('action', 'close', self.close)
			
	queue = QueueWindow('%s Version: %s' % (ADDON_NAME, VERSION))
	queue.file_id = None
	queue.set_object_event("focus", "close")
	queue.set_object_event("up", "close", "queue")
	queue.set_object_event("left", "close", "settings")
	queue.set_object_event("right", "settings", "close")
	queue.set_object_event("up", "settings", "queue")
	queue.set_object_event("down", "queue", "close")
	queue.set_object_event("right", "queue", "close")
	def poll_queue():
		working_id = False
		while True:
			if abort_poll: break
			if queue.file_id is not None:
				progress = TM.get_progress(queue.file_id)
				
				progress = progress['progress']
				if progress['id'] != 0:
					working_id = progress['id']
					if not progress['percent'] : progress['percent'] = 0
					if not progress['speed'] : progress['speed'] = 'calculating...'
					display = "[COLOR green]%s[/COLOR] bytes of [COLOR green]%s[/COLOR] at [COLOR orange]%s KBs[/COLOR]" % (format_size(progress['cached_bytes']), format_size(progress['total_bytes']), progress['speed'])
					queue.update_progress_bar('progress', float(progress['percent'])/100, display)
					queue.size.setLabel(format_size(progress['total_bytes']))
				else:
					queue.update_progress_bar('progress', 0, '')
					queue.size.setLabel('')
			else:	
				if working_id:
					queue.queue_data = TM.get_queue()['queue']
					for foo in queue.queue_data:
						index = queue.queue_data.index(foo)
						if foo[0]==working_id:
							queue.status.setLabel('complete')
							break
					working_id = False
			xbmc.sleep(1000)
	monitor = Thread(target=poll_queue)
	monitor.start()
	queue.show()
	abort_poll = True


args = ADDON.parse_query(sys.argv[2])
if args['mode'] == 		'main':
	view_queue()