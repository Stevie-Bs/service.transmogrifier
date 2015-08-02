#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import math
import xbmc,xbmcvfs
import urllib2
import shutil
import uuid
from threading import Thread
import time
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
from threadpool import *
from common import *
from vfs import VFSClass
vfs = VFSClass()

SEGMENT_SIZE = int(int(ADDON.get_setting('segment_size')) * 1000 * 1000)
CHUNK_SIZE = int(int(ADDON.get_setting('chunk_size')) * 1.024)
NUMBER_THREADS = int(ADDON.get_setting('thread_number'))
CACHE_DIRECTORY = ADDON.get_setting('save_directory')
MOVIE_DIRECTORY = vfs.join(CACHE_DIRECTORY, 'Movies')
TVSHOW_DIRECTORY = vfs.join(CACHE_DIRECTORY, 'TV Shows')
WORKING_DIRECTORY = ADDON.get_setting('work_directory')
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

class Transmogrifier():
	def __init__(self, url, filename, id, file_id, video_type='tvshow'):
		self.__abort_all = False
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
	
	def transmogrify(self, p):
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
			try:
				req = urllib2.Request(self.url, headers={"Range" : r})
				f = urllib2.urlopen(req)
				break
			except urllib2.URLError, e:
				if self.__abort_all==True:
					return p
				xbmc.sleep(2000)
				pass
		self.active_threads = self.active_threads + 1
		fp = vfs.open(file_path, 'w')
		while True:
			try:
				buff = f.read(CHUNK_SIZE)
				if not buff: break
				self.cached = self.cached + len(buff)
				fp.write(buff)
			except:
				ADDON.log("Requeue Segment %s" % p)
				p = p * -1
				return p
		return p
		
	def transmogrified(self, result):
		p = result
		if p < 0:
			p = p * -1
			self.Pool.queueTask(self.transmogrify, p, self.transmogrified)
			self.active_threads = self.active_threads - 1
			return
		self.active_threads = self.active_threads - 1
		self.completed.append(result)
		
	def assemble(self):
		ADDON.log("Waiting to assemble segments...", 1)
		if self.video_type=='tvshow':
			output_file = vfs.join(TVSHOW_DIRECTORY, vfs.clean_file_name(self.filename) + ".avi")
		else:
			output_file = vfs.join(MOVIE_DIRECTORY, vfs.clean_file_name(self.filename) + ".avi")
		stream = vfs.open(output_file, 'w')
		p=0
		while(p < self.total_segments):
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
		#try:
		now = time.time()
		delta = int(now - self.started)
		kbs = int(self.total_bytes / (delta * 1000))
		message = 'Completed %s in %s second(s) at %s KB/s.' % (self.filename, delta, kbs)
		ADDON.log(message, 1)
		ADDON.raise_notify(ADDON_NAME, message)
		#except:
		#	pass
		
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
		except:
			return False

		if self.total_bytes is False :
			return False
		return True

class Service():
	def __init__(self):
		self.__abort_all=False
		self._url = False 

	def poll_queue(self):
		SQL = "SELECT filename, url, id, video_type FROM queue WHERE status=1 ORDER BY priority, id DESC LIMIT 1"
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

		self.run()
	
	def run(self):

		ADDON.log("Service starting...", 1)
		monitor = xbmc.Monitor()
		ADDON.log("Waiting to Transmogrify...",1)
		while True:
			if monitor.waitForAbort(1) or self.__abort_all==True:
				break
			
			filename, url, id, file_id, video_type = self.poll_queue()
			if url:
				ADDON.log("Starting to Transmogrify: %s" % filename,1)
				self.id=id
				started = time.time()
				TM = Transmogrifier(url, filename, id, file_id, video_type=video_type)
				TM.start()
				DB.execute("UPDATE queue SET status=3 WHERE id=?", [self.id])
				DB.commit()
			
		ADDON.log("Service stopping...", 1)

if __name__ == '__main__':
	TS = Service()
	TS.start()