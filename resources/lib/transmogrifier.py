import re
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
		self.__block_counter = 0
		self.__video_type = video_type
		self.__filename = filename
		self.__file_id = file_id
		self.__total_blocks = total_blocks
		self.__queue = MyPriorityQueue()
		self.cache_file = vfs.join(CACHE_DIRECTORY, self.__file_id + '.temp')
		ext = '' if re.search('\.avi$', self.__filename) else '.avi'
		if video_type=='tvshow':
			self.output_file = vfs.join(TVSHOW_DIRECTORY, vfs.clean_file_name(self.__filename) + ext)
		elif video_type=='movie':
			self.output_file = vfs.join(MOVIE_DIRECTORY, vfs.clean_file_name(self.__filename) + ext)
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
		ADDON.log("write block %s %s of %s" % (block_number, self.__block_counter+1, self.__total_blocks))
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
				self.increment_counter()
			else:
				time.sleep(.1)
		self.clean_up()
		
	def increment_counter(self):
		self.__block_counter += 1	
	
	def clean_up(self):
		self.close()
		if self.__video_type != 'stream':
			vfs.rename(self.cache_file, self.output_file, quiet=True)
		

class InputHandler():
	def __init__(self, url, raw_url, file_id, total_blocks, total_bytes, headers):
		self.__headers = headers
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
		attempt = 0
		#while attempt < RETRY_ATTEMPTS *2:
		#	attempt += 1
		#	ADDON.log( "block %s attempt %s" % (block_number, attempt))
		while True:
			block = self.__call(start_byte, end_byte)
			if block: break
			time.sleep(.5)
			
				
		return block
		
	def get_block(self, block_number):
		cached = self.is_cached(block_number)
		#time.sleep(.5)
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
			# need to reprioritize queue here if delta block is greater then allowed
			return False
	
	def __call(self, start_byte, end_byte):
		r = 'bytes=%s-%s' % (start_byte, end_byte)
		#ADDON.log("Requesting remote bytes: %s" % r)
		try:
			headers = self.__headers
			headers["Range"] = r
			req = urllib2.Request(self.__url, headers=headers)
			f = urllib2.urlopen(req, timeout=2)
			if f.getcode() != 206: return False
			block = f.read(self.__block_size)
			f.close()
		except Exception, e:
			ADDON.log("HTTP Error: %s" % e)
			return False
		return block
		
class Transmogrifier():
	def __init__(self, id, url, raw_url, filename, file_id, video_type='tvshow'):
		self.win = xbmcgui.Window(10000)
		self.threads = NUMBER_THREADS
		self.block_size = BLOCK_SIZE
		self.total_bytes = 0
		self.total_blocks = 0
		self.active_threads = 0
		self.cached_bytes = 0
		self.cached_blocks = 0
		self.total_bytes = False
		self.id = id
		self.url = url
		self.filename = filename
		self.raw_url = raw_url
		self.file_id = file_id
		self.video_type = video_type
		self.Pool = ThreadPool(NUMBER_THREADS)
		self.completed = []
		self.__aborting = False
		self.set_headers(url)
	
	def set_headers(self, url):
		self.__headers = {
			'Connection': 'keep-alive',
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36',
			'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
			'Accept': 'image/webp,image/*,*/*;q=0.8',
			'Accept-Language': 'en-us,en;q=0.5',
			'Accept-Encoding': 'gzip, deflate, sdch',
		}
		temp = url.split("|")
		if len(temp) > 1:
			header_string = temp[1]
			test = re.search('User-Agent=(.+?)(&|$)+', header_string)
			if test:
				self.__headers['User-Agent'] = test.group(1)
			test = re.search('Referer=(.+?)(&|$)+', header_string)
			if test:
				self.__headers['Referer'] = test.group(1)
			test = re.search('Cookie=(.+?)(&|$)+', header_string)
			if test:
				self.__headers['Cookie'] = test.group(1)
				
	def check_abort(self):
		return get_property('abort_id') == self.file_id or self.__aborting
	
	def abort_all(self):
		if self.__aborting is False:
			self.Input.__abort = True
			clear_property('abort_id')
			clear_property(self.file_id +'.status')
			ADDON.log("Aborting Transmogrification...", 1)
			ADDON.log("Cleaning Cache...", 1)
			#vfs.rm(self.output_file, quiet=True)	# should I remove the cached file?
			ADDON.log("Waiting to Transmogrify...",1)
			self.__aborting = True
		
	def transmogrify(self, block_number):
		if self.check_abort(): 
			print "abort all"
			self.abort_all()
			return False
		block, cached = self.Input.get_block(block_number)
		if not block: 
			return [False, block_number]
		
		#if cached:	
		#	self.Output.increment_counter()
		#else:
		offset_byte = block_number * self.block_size
		self.Output.queue_block(block, offset_byte, block_number)
		self.cached_bytes += len(block)
		percent, delta, kbs = self.calculate_progress()
		self.cached_blocks += 1
		set_property(self.file_id +'.status', json.dumps({'id': self.id, 'total_bytes': self.total_bytes, 'cached_bytes': self.cached_bytes, 'cached_blocks': self.cached_blocks, 'total_blocks': self.total_blocks, 'percent': percent, 'speed': kbs}))
		ADDON.log("Progress: %s%s %s/%s %s KBs" % (percent, '%', self.cached_bytes, self.total_bytes, kbs))		
		return [True, block_number]
			
			
	def transmogrified(self, result):
		if self.check_abort(): 
			self.abort_all()
			return False
		status = result[0]
		block_number = result[1]
		if status is False:
			ADDON.log("Requeue %s" % block_number)
			self.Pool.queueTask(self.transmogrify, block_number, block_number, self.transmogrified)
		self.active_threads -= 1
		#set_property("active_threads", self.active_threads)

	def calculate_progress(self):
		try:
			now = time.time()
			delta = int(now - self.started)
			kbs = int(self.cached_bytes / (delta * 1024))
			percent = int(100 * self.cached_bytes / self.total_bytes)
			return percent, delta, kbs
		except:
			return False, False, False
		
	def start(self):
		valid = self.get_target_info()
		if valid:
			self.Output = OutputHandler(self.video_type, self.filename, self.file_id, self.total_blocks )
			self.Input = InputHandler(self.url, self.raw_url, self.file_id, self.total_blocks, self.total_bytes, self.__headers)
			self.processor = Thread(target=self.Output.process_queue)
			self.processor.start()
			self.started = time.time()
			for block_number in range(0, self.total_blocks+1):
				self.Pool.queueTask(self.transmogrify, block_number, block_number, self.transmogrified)

			
			self.processor.join()
			self.Pool.joinAll()
			percent, delta, kbs = self.calculate_progress()
			clear_property(self.file_id +'.status')
			message = 'Completed %s in %s second(s) at %s KB/s.' % (self.filename, delta, kbs)
			ADDON.log(message, 1)
			ADDON.raise_notify(ADDON_NAME, message)
		else:
			ADDON.log('Invalid url, sorry!', 1)
		
	def stream(self):
		self.Output = OutputHandler(self.video_type, self.filename, self.file_id, self.total_blocks )
		self.Input = InputHandler(self.url, self.file_id, self.total_blocks, self.total_bytes, self.__headers)
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
			req = urllib2.Request(self.url, headers=self.__headers)
			self.net = urllib2.urlopen(req, timeout=3)
			self.headers = self.net.headers.items()	
			self.total_bytes = int(self.net.headers["Content-Length"])
			self.total_blocks = int(math.ceil(self.total_bytes / self.block_size))
			ADDON.log("total blocks: %s" % self.total_blocks)
			set_property(self.file_id +'.status', json.dumps({'id': self.id, 'total_bytes': self.total_bytes, 'cached_bytes': self.cached_bytes, 'cached_blocks': 0, 'total_blocks': self.total_blocks, 'percent': 0, 'speed': 0}))
		except urllib2.URLError, e:
			ADDON.log("HTTP Error: %s" % e)
			ADDON.raise_notify("%s ERROR" % ADDON_NAME, "Unable to open URL","HTTP Error: %s" % e)
			return False
		if self.total_bytes is False :
			return False
		return True		