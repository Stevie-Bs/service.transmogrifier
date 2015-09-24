#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import urllib2
import uuid
import time
import hashlib
import urlresolver
import json
from threading import Thread
from dudehere.routines import *
from dudehere.routines.threadpool import ThreadPool, MyPriorityQueue
from BaseHTTPServer import HTTPServer
from resources.lib.common import *
from resources.lib.database import *
from resources.lib.server import RequestHandler
from resources.lib.transmogrifier import OutputHandler, Transmogrifier


class Service():
	def __init__(self):
		self._url = False 

	def poll_queue(self):
		if ADDON.get_setting('enable_transmogrifier')=='false': return False, False, False, False, False
		SQL = "SELECT filename, url, id, video_type, raw_url FROM queue WHERE status=1 ORDER BY priority, id ASC LIMIT 1"
		row = DB.query(SQL)
		if row:
			file_id = str(uuid.uuid4())
			name = row[0]
			url = row[1]
			id = row[2]
			video_type = row[3]
			raw_url = row[4]
			if raw_url and not url:
				source = urlresolver.HostedMediaFile(url=raw_url)
				url = source.resolve() if source else None
			DB.execute("UPDATE queue SET status=2, uuid=? WHERE id=?", [file_id, id])
			DB.commit()
			message = "Queued: %s" % name
			ADDON.raise_notify(ADDON_NAME, message)
			return name, url, id, file_id, video_type
		else:
			return False, False, False, False, False
		
	def start(self):
		ADDON.log("Service starting...", 1)
		monitor = xbmc.Monitor()
		ADDON.log("Waiting to Transmogrify...",1)
	
		if ADDON.get_setting('network_bind') == 'Localhost':
			address = "127.0.0.1"
		else:
			address = "0.0.0.0"
		ADDON.log("Launching WebInterface on: %s:%s" % (address, CONTROL_PORT))
		server = HTTPServer((address, CONTROL_PORT), RequestHandler)
		webserver = Thread(target=server.serve_forever)
		webserver.start()
			
		while True:
			if monitor.waitForAbort(1):
				break

			filename, url, id, file_id, video_type = self.poll_queue()
			if id:
				ADDON.log("Starting to Transmogrify: %s" % filename,1)
				self.id=id
				started = time.time()
				TM = Transmogrifier(url, filename, id, file_id, video_type=video_type)
				TM.start()
				if get_property("abort_all")=="true":
					DB.execute("UPDATE queue SET status=0 WHERE id=?", [self.id])
				else:
					DB.execute("UPDATE queue SET status=3 WHERE id=?", [self.id])
				DB.commit()

		if ADDON.get_setting('enable_webserver')=='true':
			server.socket.close()
		ADDON.log("Service stopping...", 1)

if __name__ == '__main__':
	TS = Service()
	TS.start()