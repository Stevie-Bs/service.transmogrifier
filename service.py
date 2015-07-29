#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import math
import xbmc
import urllib2
import shutil
from threading import Thread
import time
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
from threadpool import *
from common import *
from vfs import VFSClass
vfs = VFSClass()

SEGMENT_SIZE = 5 * 1000 * 1000
CHUNK_SIZE = 2 * 1024
NUMBER_THREADS = 5
CACHE_DIRECTORY = ADDON.get_setting('save_directory')
WORKING_DIRECTORY = ADDON.get_setting('work_directory')
ADDON.log("Cache Directory: %s" % CACHE_DIRECTORY)
if not vfs.exists(WORKING_DIRECTORY):
	vfs.mkdir(WORKING_DIRECTORY)
if not vfs.exists(CACHE_DIRECTORY):
	vfs.mkdir(CACHE_DIRECTORY)
from database import *
if not vfs.exists(DATA_PATH):
	vfs.mkdir(DATA_PATH)
DB_FILE = vfs.join(DATA_PATH, 'cache.db')
DB=SQLiteDatabase(DB_FILE)

class Transmorgifier():
	def __init__(self, url, filename, id):
		self.__abort_all = False
		self.threads = 5
		self.active_threads = 0
		self.cached = 0
		self.url = url
		self.filename = filename
		self.id = id
		self.Pool = ThreadPool(NUMBER_THREADS)
		self.completed = []
		self.compiled = []
	
	def transmorgify(self, p):
		start = p * SEGMENT_SIZE
		if p == self.total_segments - 1:
			end = self.total_bytes
		else:
			end = (start + SEGMENT_SIZE) - 1
		r = 'bytes=%s-%s' % (start, end)
		filename = '%s_temp.part' % str(p).zfill(3)
		file_path = vfs.join(WORKING_DIRECTORY, filename)
		ADDON.log("Requesting Segment %s/%s: %s" % (p,self.total_segments,r))
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
		
	def transmorgified(self, result):
		p = result
		if p < 0:
			p = p * -1
			self.Pool.queueTask(self.transmorgify, p, self.transmorgified)
			self._active_threads = self._active_threads - 1
			return
		self.active_threads = self.active_threads - 1
		self.completed.append(result)
		
	def assemble(self):
		ADDON.log("Waiting to assemble segments")
		output_file = vfs.join(CACHE_DIRECTORY, vfs.clean_file_name(self.filename) + ".avi")
		stream = vfs.open(output_file, 'w')
		p=0
		while(p < self.total_segments):
			if p in self.completed:
				infile = '%s_temp.part' % str(p).zfill(3)
				infile = vfs.join(WORKING_DIRECTORY, infile)
				shutil.copyfileobj(vfs.open(infile, 'r'), stream)
				ADDON.log("Assembled: %s/%s" % (p, self.total_segments))
				vfs.rm(infile, quiet=True)
				self.compiled.append(p)
				p = p+1
			xbmc.sleep(50)
		stream.close()
		DB.execute("UPDATE queue SET status=3 WHERE id=?", [self.id])
		DB.commit()
		ADDON.log("Done assembling %s" % self.name)
		
	def start(self):
		self.get_target_info()
		for p in range(0, self.total_segments):
			self.Pool.queueTask(self.transmorgify, p, self.transmorgified)
			
		assembler = Thread(target=self.assemble)
		assembler.start()
		
		self.Pool.joinAll()
		

	def get_target_info(self):
		self.net = urllib2.urlopen(self.url)
		self.headers = self.net.headers.items()
		self.total_bytes = int(self.net.headers["Content-Length"])
		self.total_segments = int(math.ceil(self.total_bytes / SEGMENT_SIZE))


class Service():
	def __init__(self):
		self.__abort_all=False
		self._url = False #'https://www.kernel.org/pub/dist/superrescue/v2/superrescue-2.1.2.iso.gz' 

	def poll_queue(self):
		SQL = "SELECT filename, url, id FROM queue WHERE status=1 ORDER BY priority, id DESC LIMIT 1"
		row = DB.query(SQL)
		if row:
			name = row[0]
			url = row[1]
			id = row[2]
			DB.execute("UPDATE queue SET status=2 WHERE id=?", [id])
			DB.commit()
			return row[0], row[1], row[2]
		else:
			return False, False, False
		
	def start(self):

		self.run()
	
	def run(self):
		ADDON.log("Service starting...")
		monitor = xbmc.Monitor()
		ADDON.log("Waiting to Transmorgify...")
		while True:
			if monitor.waitForAbort(1) or self.__abort_all==True:
				break
			
			filename, url, id = self.poll_queue()
			if url:
				TM = Transmorgifier(url, filename, id)
				TM.start()
			
		ADDON.log("Service stopping...")

if __name__ == '__main__':
	TS = Service()
	TS.start()