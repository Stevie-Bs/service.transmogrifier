import xbmcgui
import time
import math
import urllib2
from threading import Thread
from dudehere.routines import *
from dudehere.routines.threadpool import ThreadPool, MyPriorityQueue
from resources.lib.common import *

class OutputHandler():
	def __init__(self, video_type, filename, file_id, total_blocks):
		self.__abort = False
		self.__block_counter = -1
		self.__video_type = video_type
		self.__filename = filename
		self.__file_id = file_id
		self.__total_blocks = total_blocks
		self.__queue = MyPriorityQueue()
		self.cache_file = vfs.join(CACHE_DIRECTORY, self.__file_id + '.temp')	
		if video_type=='tvshow':
			self.output_file = vfs.join(TVSHOW_DIRECTORY, vfs.clean_file_name(self.__filename) + ".avi")
		elif video_type=='movie':
			self.output_file = vfs.join(MOVIE_DIRECTORY, vfs.clean_file_name(self.__filename) + ".avi")
		self.open()

	def abort_all(self):
		self.__abort = True

	def open(self):
		try:
			self.__handle = open(self.cache_file, "r+b")
		except IOError:
			self.__handle = open(self.cache_file, "wb")	
		
	def flush(self):
		self.__handle.flush()
		
	def close(self):
		self.__handle.close()

	def write_block(self, block, offset, block_number):
		self.__handle.seek(offset, 0)
		self.__handle.write(block)
		self.flush()

	def queue_block(self, block, offset, block_number):
		self.__queue.put((block, offset, block_number), offset)

	def process_queue(self):
		while self.__block_counter < self.__total_blocks:
			if self.__abort: break;
			if self.__queue.empty() is False:
				block,offset,block_number = self.__queue.get()
				self.write_block(block, offset, block_number)
				self.__block_counter += 1
			else:
				time.sleep(.1)
		self.clean_up()
	
	def clean_up(self):
		self.close()
		if self.__video_type != 'stream':
			vfs.rename(self.cache_file, self.output_file, quiet=True)
		

class InputHandler():
	def __init__(self, url, file_id, total_blocks, total_bytes):
		self.__url = url
		self.__file_id = file_id
		self.__block_size = BLOCK_SIZE
		self.__total_blocks = total_blocks
		self.__total_bytes = total_bytes
		self.__completed = []
		self.__cache_file = vfs.join(CACHE_DIRECTORY, self.__file_id + '.temp')	
	
	def is_cached(self, block_number):
		f = vfs.open(self.__cache_file, "r")
		end_byte = self.__block_size * block_number + self.__block_size -1
		f.seek(end_byte, 0)
		if f.read(1):
			f.close()
			return True
		else:
			f.close()
			return False
	def read_cached_block(self, block_number):
		f = vfs.open(self.__cache_file, "r")
		start_byte = block_number * self.__block_size
		f.seek(start_byte, 0)
		block = f.read(self.__block_size)
		f.close()
		return block
	
	def read_remote_block(self, block_number):
		start_byte = int(block_number * self.__block_size)
		end_byte = int((start_byte + self.__block_size) - 1)
		if end_byte > self.__total_bytes: end_byte = self.__total_bytes
		block = self.__call(start_byte, end_byte)
		return block
		
	def get_block(self, block_number):
		cached = self.is_cached(block_number)
		#time.sleep(.3)
		if cached:
			ADDON.log("Reading cached block %s" % block_number)
			return self.read_cached_block(block_number), cached
		else:
			ADDON.log("Reading remote block %s" % block_number)
			return self.read_remote_block(block_number), cached
		
	def read_block(self, block_number):
		cached = self.is_cached(block_number)
		if cached:
			return self.read_cached_block(block_number)
		else:
			return False
	
	def __call(self, start_byte, end_byte):
		r = 'bytes=%s-%s' % (start_byte, end_byte)
		#ADDON.log("Requesting remote bytes: %s" % r)
		try:
			req = urllib2.Request(self.__url, headers={"Range" : r})
			f = urllib2.urlopen(req, timeout=3)
			if f.getcode() != 206: return False
			block = f.read(self.__block_size)
			#f.close()
		except urllib2.URLError, e:
			ADDON.log("HTTP Error: %s" % e)
			return False
		return block
		
class Transmogrifier():
	def __init__(self, url, filename, id, file_id, video_type='tvshow'):
		self.win = xbmcgui.Window(10000)
		self.threads = NUMBER_THREADS
		self.block_size = BLOCK_SIZE
		self.total_bytes = 0
		self.total_blocks = 0
		self.active_threads = 0
		self.cached_bytes = 0
		self.total_bytes = False
		self.url = url
		self.filename = filename
		self.id = id
		self.file_id = file_id
		self.video_type = video_type
		self.Pool = ThreadPool(NUMBER_THREADS)
		self.completed = []
		self.__aborting = False
		
		#self.set_property('abort_all', "false")
		#self.set_property('threads', self.threads)
		#self.set_property('active_threads', self.active_threads)
		#self.set_property('cached_bytes', self.cached_bytes)
		#self.set_property('total_bytes', self.total_bytes)
		#self.set_property('filename', self.filename)
		#self.set_property('id', self.id)
		#self.set_property('file_id', self.file_id)
		#self.set_property('percent', 0)
	
	def check_abort(self):
		return get_property('abort_id') == self.file_id or self.__aborting
	
	def abort_all(self):
		if self.__aborting is False:
			self.Input.__abort = True
			clear_property('abort_id')
			ADDON.log("Aborting Transmogrification...", 1)
			ADDON.log("Cleaning Cache...", 1)
			#vfs.rm(self.output_file, quiet=True)
			#self.set_property('percent', 0)
			#self.set_property('cached_bytes', 0)
			#self.set_property('total_bytes', 'False')
			#self.set_property('id', '')
			#self.set_property('speed', '')
			#self.set_property('delta', '')
			ADDON.log("Waiting to Transmogrify...",1)
			self.__aborting = True
		
	def transmogrify(self, block_number):
		if self.check_abort(): 
			self.abort_all()
			return False
		block, cached = self.Input.get_block(block_number)
		if not block: return block_number * -1
		#if not cached:
		offset_byte = block_number * self.block_size
		#print offset_byte
		self.Output.queue_block(block, offset_byte, block_number)
		self.cached_bytes += len(block)
		#percent, delta, kbs = self.calculate_progress()	
		#self.set_property('cached_bytes', self.cached_bytes)
		#self.set_property("percent", percent)
		#self.set_property("speed", kbs)
		#ADDON.log("Progress: %s%s %s/%s %s KBs" % (percent, '%', self.cached_bytes, self.total_bytes, kbs))		
		return block_number
			
	

		
	def transmogrified(self, block_number):
		if self.check_abort(): 
			self.abort_all()
			return False
		if block_number < 0:
			block_number = block_number * -1
			print "requeue %s" % block_number
			self.Pool.queueTask(self.transmogrify, block_number, self.transmogrified)
		self.active_threads -= 1
		#set_property("active_threads", self.active_threads)

	def calculate_progress(self):
		try:
			now = time.time()
			delta = int(now - self.started)
			kbs = int(self.cached_bytes / (delta * 1000))
			percent = int(100 * self.cached_bytes / self.total_bytes)
			return percent, delta, kbs
		except:
			return False, False, False
		
	def start(self):
		valid = self.get_target_info()
		if valid:
			self.Output = OutputHandler(self.video_type, self.filename, self.file_id, self.total_blocks )
			self.Input = InputHandler(self.url, self.file_id, self.total_blocks, self.total_bytes)
			self.processor = Thread(target=self.Output.process_queue)
			self.processor.start()
			self.started = time.time()
			for block_number in range(0, self.total_blocks+1):
				self.Pool.queueTask(self.transmogrify, block_number, self.transmogrified)

			self.Pool.joinAll()
			self.processor.join()
			#percent, delta, kbs = self.calculate_progress()
			#self.set_property("percent", 100)
			#message = 'Completed %s in %s second(s) at %s KB/s.' % (self.filename, delta, kbs)
			#ADDON.log(message, 1)
			#ADDON.raise_notify(ADDON_NAME, message)
		else:
			ADDON.log('Invalid url, sorry!', 1)
		
	def stream(self):
		self.Output = OutputHandler(self.video_type, self.filename, self.file_id, self.total_blocks )
		self.Input = InputHandler(self.url, self.file_id, self.total_blocks, self.total_bytes)
		self.processor = Thread(target=self.Output.process_queue)
		self.processor.start()
		self.started = time.time()
		for block_number in range(0, self.total_blocks+1):
			self.Pool.queueTask(self.transmogrify, block_number, self.transmogrified)
		return True

	def seek(self):
		self.Input = InputHandler(self.url, self.file_id, self.total_blocks, self.total_bytes)
	
	def read_block(self, start_byte=0):
		end_byte = (start_byte + self.block_size) - 1
		if end_byte > self.total_bytes: end_byte = self.total_bytes
		block_number = self.get_block_number_from_byte(start_byte)
		block = self.Input.read_block(block_number)
		if block:
			return block, end_byte
		else:
			return False, start_byte

	def get_block_number_from_byte(self, start_byte):
		block_number = int(math.floor(float(start_byte) / self.block_size))
		return block_number

	def get_target_info(self):
		try:
			self.net = urllib2.urlopen(self.url)
			self.headers = self.net.headers.items()	
			self.total_bytes = int(self.net.headers["Content-Length"])
			self.total_blocks = int(math.ceil(self.total_bytes / self.block_size))
			ADDON.log("total blocks: %s" % self.total_blocks)
			#self.set_property("total_bytes", self.total_bytes)
			#self.set_property("total_blocks", self.total_blocks)
		except:
			return False
		if self.total_bytes is False :
			return False
		return True		