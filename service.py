#!/usr/bin/python
# -*- coding: utf-8 -*-
import xbmc
import urllib2
import uuid
import time
import hashlib
import urlresolver
import json
import socket
import errno
from threading import Thread
from SocketServer import ThreadingMixIn
from dudehere.routines import *
from resources.lib.database import *
from dudehere.routines.vfs import VFSClass
from dudehere.routines.threadpool import ThreadPool, MyPriorityQueue
from BaseHTTPServer import HTTPServer
from resources.lib.common import *

from resources.lib.server import RequestHandler
from resources.lib.transmogrifier import OutputHandler, Transmogrifier

class Server(HTTPServer):
		
	def get_request(self):
		self.socket.settimeout(5.0)
		result = None
		while result is None:
			try:
				result = self.socket.accept()
			except socket.timeout:
				pass
		result[0].settimeout(1000)
		return result
	
	def _handle_request_noblock(self):
		"""Handle one request, without blocking.

		I assume that select.select has returned that the socket is
		readable before this function was called, so there should be
		no risk of blocking in get_request().
		"""
		try:
			request, client_address = self.get_request()
		except socket.error, e:
			if isinstance(e.args, tuple):
				print "errno is %d" % e[0]
				if e[0] == errno.EPIPE:
					print "Detected remote disconnect"
				else:
					print e
			else:
				print "socket error ", e
		if self.verify_request(request, client_address):
			try:
				self.process_request(request, client_address)
			except:
				self.handle_error(request, client_address)
				self.shutdown_request(request)

class ThreadedHTTPServer(ThreadingMixIn, Server):
	"""Handle requests in a separate thread."""

class Service(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self, *args, **kwargs)
	
	def onPlayBackStarted(self):
		if get_property('streaming.started'):
			ADDON.log("Now I'm playing file id: %s " % get_property('file_id'))
	
	def onPlayBackStopped(self):
		if get_property('streaming.started'):
			vfs = VFSClass()
			ADDON.log("Now I'm stopped")
			ADDON.log("Abort: %s" % get_property('file_id'))
			set_property("abort_id", get_property('file_id'))
			tail_file = vfs.join(WORK_DIRECTORY, get_property('file_id') + '.tail')
			if vfs.exists(tail_file):
				vfs.rm(tail_file,quiet=True)
			time.sleep(0.25)
			clear_property("abort_id")
			clear_property('playing')
			clear_property('file_id')
			clear_property('streaming.started')
			clear_property("streaming.total_bytes")
			clear_property("streaming.total_blocks")
			clear_property("streaming.file_id")
			clear_property("streaming.abort")
			clear_property("streaming.seek_block")
			clear_property('streaming.tail_requested')
	
	def onPlayBackEnded(self):
		self.onPlayBackStopped()
		

	def poll_queue(self):
		self.DB.connect()
		if ADDON.get_setting('enable_transmogrifier')=='false': return False, False, False, False, False, False, False
		SQL = "SELECT filename, url, id, video_type, raw_url, save_dir FROM queue WHERE status=1 ORDER BY priority DESC, id LIMIT 1"
		row = self.DB.query(SQL)
		if row:
			name = row[0]
			url = row[1]
			video_type = row[3]
			id = row[2]
			raw_url = row[4]
			save_dir = row[5]
			file_id = hashlib.md5(url).hexdigest()
			if raw_url and not url:
				source = urlresolver.HostedMediaFile(url=raw_url)
				url = source.resolve() if source else None
			self.DB.execute("UPDATE queue SET status=2, fileid=? WHERE id=?", [file_id, id])
			self.DB.commit()
			message = "Queued: %s" % name
			ADDON.raise_notify(ADDON_NAME, message)
			return name, url, raw_url, id, file_id, video_type, save_dir
		else:
			return False, False, False, False, False, False, False
	
	def clear_cache(self):
		if ADDON.get_setting('clear_cache') == "true":
			vfs = VFSClass()
			ADDON.log("Clearing download cache...")
			files = vfs.ls(WORK_DIRECTORY, pattern='state$|temp$|tail$')
			for foo in files[1]:
				path = vfs.join(WORK_DIRECTORY, foo)
				vfs.rm(path, quiet=True)
		ADDON.log("Clearing orphaned jobs...")
		self.DB.connect()
		self.DB.execute("UPDATE queue SET status=-1 WHERE status=2")
		self.DB.commit()

		
	def start(self):
		if DB_TYPE == 'sqlite':
			self.DB = MyDatabaseAPI(DB_FILE, connect=False, quiet=True, check_version=False)
		else:
			self.DB = DB
		ADDON.log("Service starting...", 1)
		monitor = xbmc.Monitor()
		self.clear_cache()
		ADDON.log("Waiting to Transmogrify...",1)
		if ADDON.get_setting('network_bind') == 'Localhost':
			address = "127.0.0.1"
		else:
			address = "0.0.0.0"
		ADDON.log("Launching WebInterface on: %s:%s" % (address, CONTROL_PORT))
		
		server_class = ThreadedHTTPServer
		httpd = server_class((address, CONTROL_PORT), RequestHandler)
		webserver = Thread(target=httpd.serve_forever)
		webserver.start()
		self.DB.connect()
		while not monitor.abortRequested():
			if monitor.waitForAbort(1) or get_property('service.abort'):
				break
			filename, url, raw_url, id, file_id, video_type, save_dir = self.poll_queue()
			if id:
				ADDON.log("Starting to Transmogrify: %s" % filename,1)
				self.id=id
				started = time.time()
				set_property("caching.file_id", file_id)
				TM = Transmogrifier(id, url, raw_url, filename, file_id, video_type=video_type, save_dir=save_dir)
				TM.start()
				
				if get_property("abort_all")=="true":
					self.DB.execute("UPDATE queue SET status=-1 WHERE id=?", [self.id])
				else:
					set_property("caching.complete", file_id)
					self.DB.execute("UPDATE queue SET status=3 WHERE id=?", [self.id])
					try:
						if NOTIFICATION:
							from subprocess import call
							wav = vfs.join(ROOT_PATH, 'resources/notifications/'+NOTIFICATION+'.wav')
							if PLATFORM.startswith('linux'):
								call(["aplay", wav])
							elif PLATFORM.startswith('darwin'):
								call(["afplay"], wav)
							elif PLATFORM.startswith('win'):
								import winsound
								winsound.PlaySound(wav, winsound.SND_FILENAME)
					except: pass
				self.DB.commit()
				del TM
		
		httpd.socket.close()
		ADDON.log("Service stopping...", 1)
		
if __name__ == '__main__':
	TS = Service()
	TS.start()
	TS.DB.disconnect()