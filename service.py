#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import math
import string
import cgi
from os import curdir, sep
from urlparse import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import xbmc,xbmcvfs,xbmcgui
import urllib2
import shutil
import uuid
from threading import Thread
import time
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
from threadpool import *
from common import *
from vfs import VFSClass
try: 
	import simplejson as json
except ImportError: 
	import json
vfs = VFSClass()
DISABLED = False

SEGMENT_SIZE = int(float(ADDON.get_setting('segment_size')) * 1000 * 1000)
CHUNK_SIZE = int(ADDON.get_setting('chunk_size'))
NUMBER_THREADS = int(ADDON.get_setting('thread_number'))
CACHE_DIRECTORY = ADDON.get_setting('save_directory')
MOVIE_DIRECTORY = vfs.join(CACHE_DIRECTORY, 'Movies')
TVSHOW_DIRECTORY = vfs.join(CACHE_DIRECTORY, 'TV Shows')
WORKING_DIRECTORY = ADDON.get_setting('work_directory')
WINDOW_PREFIX = 'transmogrifier'
WEB_ROOT = vfs.join(ROOT_PATH, 'resources/www/html')
CONTROL_PORT = int(ADDON.get_setting('control_port'))


ADDON.log({"segment_size": SEGMENT_SIZE, "chunk_size": CHUNK_SIZE, "thread_number": NUMBER_THREADS})
ADDON.log("Work Directory: %s" % WORKING_DIRECTORY)
ADDON.log("Cache Directory: %s" % CACHE_DIRECTORY)
if not vfs.exists(WORKING_DIRECTORY): vfs.mkdir(WORKING_DIRECTORY)
if not vfs.exists(CACHE_DIRECTORY): vfs.mkdir(CACHE_DIRECTORY)
if not vfs.exists(MOVIE_DIRECTORY): vfs.mkdir(MOVIE_DIRECTORY)
if not vfs.exists(TVSHOW_DIRECTORY): vfs.mkdir(TVSHOW_DIRECTORY)
	
from database import *
if not vfs.exists(DATA_PATH):
	vfs.mkdir(DATA_PATH)
DB_FILE = vfs.join(DATA_PATH, 'cache.db', ADDON.get_setting('log_level')==0)
DB=SQLiteDatabase(DB_FILE)

def set_property(k, v):
	k = "%s.%s" % (WINDOW_PREFIX, k)
	xbmcgui.Window(10000).setProperty(k, str(v))
	
def get_property(k):
	k = "%s.%s" % (WINDOW_PREFIX, k)
	p = xbmcgui.Window(10000).getProperty(k)
	if p == 'false': return False
	if p == 'true': return True
	return p

class RequestHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		parts = urlparse(self.path)
		try:
			path = parts.path
			query = parts.query
			data = cgi.parse_qs(query, keep_blank_values=True)
			if path == '/query/':
				if data['method'][0] == 'getLogContent':
					logfile = vfs.join('special://temp', 'kodi.log')
					f = open(logfile)
					contents = f.read()
					f.close()
					contents = re.sub('<host>(.+?)</host>', '<pass>******</pass>', contents)
					contents = re.sub('<name>(.+?)</name>', '<name>******</name>', contents)
					contents = re.sub('<user>(.+?)</user>', '<user>******</user>', contents)
					contents = re.sub('<pass>(.+?)</pass>', '<pass>******</pass>', contents)
					self.do_Response(contents, 'text/plain')
				elif data['method'][0] == 'getProgress':
					response = {
							"id": get_property('id'), 
							"cached_bytes": get_property('cached'),
							"total_bytes": get_property('total_bytes'),
							"percent": get_property('percent'),
					}
					self.do_Response(json.dumps(response))
				elif data['method'][0] == 'deleteQueue':
					DB=SQLiteDatabase(DB_FILE)
					DB.execute("DELETE FROM queue WHERE id=?", [data['id'][0]])
					DB.commit()
					self.do_Response("{'status': 200, 'message': 'success'}")
				elif data['method'][0] == 'restartQueue':
					DB=SQLiteDatabase(DB_FILE)
					DB.execute("UPDATE queue SET status=1 WHERE id=?", [data['id'][0]])
					DB.commit()
					self.do_Response("{'status': 200, 'message': 'success'}")
				elif data['method'][0] == 'abortQueue':
					set_property("abort_all", "true")
					self.do_Response("{'status': 200, 'message': 'success'}")						
				elif data['method'][0] == 'getQueue':
					DB=SQLiteDatabase(DB_FILE)
					rows = DB.query("SELECT id, video_type, filename, status, raw_url FROM queue ORDER BY id ASC", force_double_array=True)
					self.do_Response(json.dumps(rows))
				elif data['method'][0] == 'getTVShows':
					shows = vfs.ls(TVSHOW_DIRECTORY)
					results = []
					for show in shows[1]:
						results.append(show)
					self.do_Response(json.dumps(results))
				elif data['method'][0] == 'getMovies':
					movies = vfs.ls(MOVIE_DIRECTORY)
					results = []
					for movie in movies[1]:
						results.append(movie)
					self.do_Response(json.dumps(results))
				elif data['method'][0] == 'downloadFile':
					if data['media'][0] == 'movie':
						path = vfs.join(MOVIE_DIRECTORY, data['file'][0])
					else:
						path = vfs.join(TVSHOW_DIRECTORY, data['file'][0])
					if not vfs.exists(path):
						self.send_error(404,'File Not Found: %s' % self.path)
						return False
					f = open(path, "r")
					
					self.send_response(200)
					self.send_header("Pragma", "public")
					self.send_header("Expires", "0")
					self.send_header("Cache-Control", "must-revalidate, post-check=0, pre-check=0")
					self.send_header("Content-Type", "application/force-download")
					self.send_header("Content-Type", "application/octet-stream")
					self.send_header("Content-Type", "application/download")
					self.send_header("Content-Disposition", 'attachment; filename="%s"' % data['file'][0]);
					self.end_headers()
					self.wfile.write(f.read())
					f.close()
				else:
					self.do_Response("{'status': 200, 'message': 'success'}")
				return True
			else:
				if self.path=='/':
					self.path='/index.html'
				
				fileName, fileExtension = os.path.splitext(self.path)
				headers = {
						'.css': 	'text/css',
						'.js':		'application/javascript',
						'.ico':		'image/x-icon',
						'.jpg':		'image/jpeg',
						'.png':		'image/png',
						'.gif':		'image/gif',
						'.html':	'text/html',
						'.txt':		'text/plain',
				}
				if fileExtension not in headers.keys():
					self.send_error(403,'Forbidden')
					return False
				
				full_path = WEB_ROOT + os.sep +  self.path
				
				if not vfs.exists(full_path):
					self.send_error(404,'File Not Found: %s' % self.path)
					return False
				self.send_response(200)
				self.send_header('Content-type',	headers[fileExtension])
				f = open(full_path) 
				
				self.end_headers()
				self.wfile.write(f.read())
				f.close()
				return True
			return True
		except IOError:
			self.send_error(500,'Internal Server Error')
			return False
	def do_POST(self):
		try:
			ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
			if ctype == 'multipart/form-data':
				query=cgi.parse_multipart(self.rfile, pdict)
				print query
			self.send_response(301)

			self.end_headers()
			upfilecontent = query.get('upfile')
			print "filecontent", upfilecontent[0]
			self.wfile.write("<HTML>POST OK.<BR><BR>");
			self.wfile.write(upfilecontent[0]);
		except:
			self.send_error(500,'Internal Server Error')
			
	def do_Response(self, content, content_type='application/json', response=200):
		self.send_response(response)
		self.send_header('Content-type',	content_type)
		self.end_headers()
		self.wfile.write(content)
		
class Transmogrifier():
	def __init__(self, url, filename, id, file_id, video_type='tvshow'):
		self.win = xbmcgui.Window(10000)
		self.threads = NUMBER_THREADS
		self.active_threads = 0
		self.cached = 0
		self.total_bytes = False
		self.url = url
		self.filename = filename
		self.id = id
		self.file_id = file_id
		self.video_type = video_type
		self.Pool = ThreadPool(NUMBER_THREADS)
		self.completed = []
		self.compiled = []
		self.total_bytes = 0
		
		self.set_property('abort_all', "false")
		self.set_property('threads', self.threads)
		self.set_property('active_threads', self.active_threads)
		self.set_property('cached', self.cached)
		self.set_property('total_bytes', self.total_bytes)
		self.set_property('filename', self.filename)
		self.set_property('id', self.id)
		self.set_property('file_id', self.file_id)
		self.set_property('percent', 0)
	
	def check_abort(self):
		return self.get_property('abort_all')
	
	def abort_all(self):
		ADDON.log("Aborting Transmogrification...", 1)
		ADDON.log("Cleaning Cache...", 1)
		vfs.rm(self.output_file, quiet=True)
		for p in range(0, self.total_segments):
			filename = '%s_%s.part' % (str(p).zfill(3), self.file_id)
			temp_file = vfs.join(WORKING_DIRECTORY, filename)
			if vfs.exists(temp_file):
				vfs.rm(temp_file, quiet=True)
		vfs.rm(self.output_file, quiet=True)
		self.set_property('percent', 0)
		self.set_property('cached', 0)
		self.set_property('total_bytes', 'False')
		self.set_property('id', '')
		ADDON.log("Waiting to Transmogrify...",1)
		
	def set_property(self, k, v):
		k = "%s.%s" % (WINDOW_PREFIX, k)
		self.win.setProperty(k, str(v))
	
	def get_property(self, k):
		k = "%s.%s" % (WINDOW_PREFIX, k)
		p = self.win.getProperty(k)
		if p == 'false': return False
		if p == 'true': return True
		return p
	
	def transmogrify(self, p):
		if self.check_abort(): return p
		start = p * SEGMENT_SIZE
		if p == self.total_segments - 1:
			end = self.total_bytes
		else:
			end = (start + SEGMENT_SIZE) - 1
		r = 'bytes=%s-%s' % (start, end)
		filename = '%s_%s.part' % (str(p).zfill(3), self.file_id)
		file_path = vfs.join(WORKING_DIRECTORY, filename)
		ADDON.log("Requesting Segment %s/%s: %s" % ((p+1),self.total_segments,r))
		while True:
			if self.check_abort(): return p
			try:
				req = urllib2.Request(self.url, headers={"Range" : r})
				f = urllib2.urlopen(req)
				break
			except urllib2.URLError, e:
				if self.check_abort(): return p
				xbmc.sleep(2000)
				pass
		self.active_threads = self.active_threads + 1
		self.set_property("active_threads", self.active_threads)
		fp = vfs.open(file_path, 'w')
		while True:
			if self.check_abort(): return p
			try:
				buff = f.read(CHUNK_SIZE)
				if not buff: break
				self.cached = self.cached + len(buff)
				fp.write(buff)
				delta, kbs = self.calculate_progress()
				self.set_property("cached", self.cached)
				self.set_property("time_delta", delta)
			except Exception, e:
				print e
				ADDON.log("Requeue Segment %s" % p)
				p = p * -1
				return p
			percent = int(100 * self.cached / self.total_bytes)
			self.set_property("percent", percent)
		#percent = int(100 * self.cached / self.total_bytes)
		ADDON.log("Progress: %s%s %s/%s %s KBs" % (percent, '%', self.cached, self.total_bytes, kbs))
		return p
		
	def transmogrified(self, result):
		p = result
		if p < 0:
			p = p * -1
			self.Pool.queueTask(self.transmogrify, p, self.transmogrified)
			self.active_threads = self.active_threads - 1
			self.set_property("active_threads", self.active_threads)
			return
		self.active_threads = self.active_threads - 1
		self.set_property("active_threads", self.active_threads)
		self.completed.append(result)
		
	def assemble(self):
		ADDON.log("Waiting to assemble segments...", 1)
		if self.video_type=='tvshow':
			self.output_file = vfs.join(TVSHOW_DIRECTORY, vfs.clean_file_name(self.filename) + ".avi.temp")
			final_file = vfs.join(TVSHOW_DIRECTORY, vfs.clean_file_name(self.filename) + ".avi")
		else:
			self.output_file = vfs.join(MOVIE_DIRECTORY, vfs.clean_file_name(self.filename) + ".avi.temp")
			final_file = vfs.join(MOVIE_DIRECTORY, vfs.clean_file_name(self.filename) + ".avi")
		stream = vfs.open(self.output_file, 'w')
		p=0
		while(p < self.total_segments):
			if self.check_abort(): 
				self.abort_all()
				return p
			if p in self.completed:
				infile = '%s_%s.part' % (str(p).zfill(3), self.file_id)
				infile = vfs.join(WORKING_DIRECTORY, infile)
				shutil.copyfileobj(vfs.open(infile, 'r'), stream)
				ADDON.log("Assembled: %s/%s" % ((p+1), self.total_segments))
				vfs.rm(infile, quiet=True)
				self.compiled.append(p)
				p = p+1
			xbmc.sleep(50)
		stream.close()
		delta, kbs = self.calculate_progress()
		self.set_property("percent", 100)
		vfs.rename(self.output_file, final_file, quiet=True)
		message = 'Completed %s in %s second(s) at %s KB/s.' % (self.filename, delta, kbs)
		ADDON.log(message, 1)
		ADDON.raise_notify(ADDON_NAME, message)
	
	def calculate_progress(self):
		try:
			now = time.time()
			delta = int(now - self.started)
			kbs = int(self.total_bytes / (delta * 1000))
			return delta, kbs
		except:
			return False, False
	def start(self):
		valid = self.get_target_info()
		if valid:
			self.started = time.time()
			for p in range(0, self.total_segments):
				self.Pool.queueTask(self.transmogrify, p, self.transmogrified)
				
			assembler = Thread(target=self.assemble)
			assembler.start()
			self.Pool.joinAll()
		else:
			ADDON.log('Invalid url, sorry!', 1)
		

	def get_target_info(self):
		try:
			self.net = urllib2.urlopen(self.url)
			self.headers = self.net.headers.items()
			self.total_bytes = int(self.net.headers["Content-Length"])
			self.total_segments = int(math.ceil(self.total_bytes / SEGMENT_SIZE))
			self.set_property("total_bytes", self.total_bytes)
		except:
			return False

		if self.total_bytes is False :
			return False
		return True

class Service():
	def __init__(self):
		self._url = False 

	def poll_queue(self):
		if ADDON.get_setting('enable_transmogrifier')=='false': return False, False, False, False, False
		SQL = "SELECT filename, url, id, video_type FROM queue WHERE status=1 ORDER BY priority, id ASC LIMIT 1"
		row = DB.query(SQL)
		if row:
			file_id = str(uuid.uuid4())
			name = row[0]
			url = row[1]
			id = row[2]
			video_type = row[3]
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
		if ADDON.get_setting('enable_webserver')=='true':
			ADDON.log("Launching WebInterface on port: " + str(CONTROL_PORT))
			server = HTTPServer(('', CONTROL_PORT), RequestHandler)
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