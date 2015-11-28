#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import math
import xbmc,xbmcgui
from threading import Thread
from dudehere.routines import *
from dudehere.routines.window import Window
from dudehere.routines.constants import WINDOW_ACTIONS
from dudehere.routines.transmogrifier import TransmogrifierAPI
from dudehere.routines.vfs import VFSClass
vfs = VFSClass()
	
WINDOW_PREFIX = 'transmogrifier'
CONTEX_ACTION = None
STATUS = enum(PENDING=1, ACTIVE=2, COMPLETE=3, PAUSED=4, FAILED=-1)
FIELDS = enum(STATUS="label", FILENAME="originaltitle", SIZE="title", PATH="album", IMDB="code", YEAR="year", EPISODE="episode", SEASON="season", PRIORITY="top250", ADDON="director")
status_icons = {1: "pending.png", 2: "active.png", 3: "complete.png", -1: "failed.png"}
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

def reset_db():
	from dudehere.routines.plugin import Plugin
	plugin = Plugin()
	c = plugin.confirm("Reset Database", "Are you sure?", "You will have to restart kodi afterwards.")
	if c:
		DB_FILE = ADDON.get_setting('database_sqlite_file')
		ADDON.set_setting("database_sqlite_init", "false")
		vfs.rm(DB_FILE, quiet=True)
		
def select_host():
	from dudehere.routines.plugin import Plugin
	plugin = Plugin()
	hosts_file = vfs.join(DATA_PATH, "hosts.json")
	if vfs.exists(hosts_file):
		history = vfs.read_file(hosts_file, json=True)
		hosts = ["http://%s:%s" % (h['host'], h['port']) for h in history]
		host = plugin.dialog_select('Select a Host', hosts)
		if host is not False:
			host = history[host]
			ADDON.set_setting('remote_host', host['host'])
			ADDON.set_setting('remote_control_port', host['port'])
			ADDON.set_setting('remote_auth_pin', host['pin'])
	else:
		plugin.notify("Error", "Host history is empty")
	
	
	
def view_queue():
	TM = TransmogrifierAPI()
	
	class Queue(xbmcgui.WindowXMLDialog):
		abort_polling = False
		current_id = -1
		def __init__(self, *args, **kwargs):
			xbmcgui.WindowXML.__init__(self)
		
		def poll_queue(self):
			while True:
				if self.abort_polling: break
				results = TM.get_progress()
				self.update(results)
				xbmc.sleep(1000)
			
		def onInit(self):
			connection = "[B][COLOR blue]http://%s:%s[/COLOR][/B]"
			if ADDON.get_setting('connect_remote') == 'true':
				connection = connection % (ADDON.get_setting('remote_host'), ADDON.get_setting('remote_control_port'))
				hosts_file = vfs.join(DATA_PATH, "hosts.json")
				if vfs.exists(hosts_file):
					history = vfs.read_file(hosts_file, json=True)
				else:
					history = []
				old_host = False
				for h in history: 
					old_host = (h['host'] == ADDON.get_setting('remote_host') and h['port'] == ADDON.get_setting('remote_control_port'))
					if old_host: break
				if not old_host:
					history.append({"host": ADDON.get_setting('remote_host'), "port": ADDON.get_setting('remote_control_port'), "pin": ADDON.get_setting('remote_auth_pin')})	
				vfs.write_file(hosts_file, history, mode='w', json=True)
			else:
				connection = connection % ('localhost', ADDON.get_setting('control_port'))
			self.getControl(80013).setLabel(connection)
			queue = TM.get_queue()
			self.update(queue)
			monitor = Thread(target=self.poll_queue)
			monitor.start()
		
		def show_context(self, index, status):
			global CONTEX_ACTION
			CONTEX_ACTION = None
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
						icon = item.replace(" ", "_").lower()
						icon = vfs.join(icon_root, icon + '.png')

						self.get_object('dialog').getListItem(index).setIconImage(icon)
					self.set_object_event('focus', 'dialog')
			
			context = ContextWindow("Queue")
			status=int(status)
			if status == STATUS.PENDING:
				context.items = ["Remove", "Change Priority"]
			elif status == STATUS.ACTIVE:
				context.items = ["Abort"]
			elif status == STATUS.COMPLETE:
				context.items = ["Requeue", "Remove"]
			elif status == STATUS.PAUSED:
				context.items = ["Requeue", "Remove", "Resume"]
			else:
				context.items = ["Requeue", "Remove"]
			context.show()
			del context
			return CONTEX_ACTION
		
		def update(self, queue):
			items = []
			try:
				if queue['progress']['id'] != 0:
					for test in queue['queue']:
						if test[0] == queue['progress']['id']:
							self.getControl(80010).setLabel('Active')
							self.getControl(80011).setLabel(test[2])
							self.getControl(80012).setLabel(test[7])
							current_id = queue['progress']['id']
							break
					self.getControl(80050).setPercent(queue['progress']['percent'])
					self.getControl(80014).setLabel(format_size(queue['progress']['total_bytes']))
					status = "[COLOR green]%s[/COLOR] of [COLOR green]%s[/COLOR] at [COLOR orange]%s KB/s[/COLOR] %s%s" % (format_size(queue['progress']['cached_bytes']), format_size(queue['progress']['total_bytes']), queue['progress']['speed'], queue['progress']['percent'], '%')
					self.getControl(80015).setLabel(status)
				else:
					self.getControl(80050).setPercent(0)
					self.getControl(80010).setLabel("")
					self.getControl(80011).setLabel("")
					self.getControl(80012).setLabel("")
					self.getControl(80014).setLabel("")
					self.getControl(80015).setLabel("")
					current_id = 0
			except: 
				self.getControl(80050).setPercent(0)
				self.getControl(80010).setLabel("")
				self.getControl(80011).setLabel("")
				self.getControl(80012).setLabel("")
				self.getControl(80014).setLabel("")
				self.getControl(80015).setLabel("")
				current_id = 0
			if self.current_id != current_id:
				for item in queue['queue']:
					status = status_icons[item[3]]
					liz = xbmcgui.ListItem(status, iconImage=item[1]+".png")
					liz.setInfo("Video", {FIELDS.PRIORITY: item[6], FIELDS.FILENAME: item[2], FIELDS.ADDON: item[7]})
					liz.setProperty("status", str(item[3]))
					liz.setProperty("file_id", str(item[5]))
					liz.setProperty("id", str(item[0]))
					items.append(liz)
				self.getControl(80000).reset()
				self.getControl(80000).addItems(items)
				self.current_id = current_id

		def onAction(self, action):
			action = action.getId()
			if action in [WINDOW_ACTIONS.ACTION_PREVIOUS_MENU, WINDOW_ACTIONS.ACTION_NAV_BACK]:
				self.close()
			
			try:
				if action in [WINDOW_ACTIONS.ACTION_SHOW_INFO, WINDOW_ACTIONS.ACTION_CONTEXT_MENU]:
					controlID = self.getFocus().getId()
					if controlID == 80000:
						index = self.getControl(controlID).getSelectedPosition()
						liz = self.getControl(controlID).getListItem(index)
						status = liz.getProperty("status")
						event = self.show_context(index, status)
						id = int(liz.getProperty("id"))
						file_id = liz.getProperty("file_id")
						if event == 'requeue':
							TM.restart(id)
						elif event == 'abort':
							TM.abort(file_id)
						elif event == 'remove':
							TM.delete(int(id))
							self.getControl(controlID).removeItem(index)
						elif event == 'change priority':
							dialog = xbmcgui.Dialog()
							priority = dialog.numeric(0, 'Enter a new Priority', "10")
							TM.change_priority(id, priority)
							self.current_id = -1
							queue = TM.get_queue()
							self.update(queue)
			except:
				pass
			
		def onClick(self, controlID):
			pass
			if controlID in [82003, 82000]: 
				self.close()
			elif controlID==82001:
				TM.clean_queue()
				#self.current_id = -1
				#queue = TM.get_queue()
				#self.update(queue)

		
		def onFocus(self, controlID):
			pass

	q = Queue("queue.xml", ROOT_PATH)
	q.doModal()
	q.abort_polling = True
	del q


args = ADDON.parse_query(sys.argv[2])
if args['mode'] == 		'main':
	view_queue()
elif args['mode'] ==	'reset_db':
	reset_db()
elif args['mode'] ==	'select_host':
	select_host()	
