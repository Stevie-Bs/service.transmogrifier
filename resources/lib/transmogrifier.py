import re
import xbmcgui
import time
import math
import urllib2
import random
import Queue
from threading import Thread
from dudehere.routines import *
from dudehere.routines.threadpool import ThreadPool, MyPriorityQueue
from resources.lib.common import *

def change_thread_count(delta):
	active_threads = int(get_property("active_threads")) + delta
	set_property("active_threads", str( active_threads ))

def set_thread_count(threads):
	set_property("active_threads", str( threads ))
	
class OutputHandler():
	def __init__(self, video_type, filename, file_id, total_blocks, completed_blocks = [], extension='avi', save_dir=False):
		self.__abort = False
		self.__block_counter = 0
		self.__video_type = video_type
		self.__filename = filename
		self.__file_id = file_id
		self.__total_blocks = total_blocks
		self.__completed_blocks = completed_blocks
		self.__queue = MyPriorityQueue()
		self.__stream_disk_caching = ADDON.get_setting('stream_caching') == 'Disk'
		
		self.cache_file = vfs.join(WORK_DIRECTORY, self.__file_id + '.temp')
		self.state_file = vfs.join(WORK_DIRECTORY, self.__file_id + '.state')
		if video_type=='tvshow':
			save_dir = save_dir if save_dir else TVSHOW_DIRECTORY
			self.output_file = vfs.join(save_dir, vfs.clean_file_name(self.__filename) + '.' + extension)
		elif video_type=='movie':
			save_dir = save_dir if save_dir else MOVIE_DIRECTORY
			self.output_file = vfs.join(save_dir, vfs.clean_file_name(self.__filename) + '.' + extension)
		self.open()

	def abort_all(self):
		self.__abort = True

	def open(self):
		try:
			self.__handle = open(self.cache_file, "r+b")
			#self.__handle = vfs.open(self.cache_file, "r+b")
		except IOError:
			self.__handle = open(self.cache_file, "wb")
			#self.__handle = vfs.open(self.cache_file, "wb")
		
	def flush(self):
		self.__handle.flush()
		
	def close(self):
		self.__handle.close()

	def write_block(self, block, offset, block_number):
		ADDON.log("write block %s %s of %s" % (block_number, self.__block_counter+1, self.__total_blocks), LOG_LEVEL.STANDARD)
		self.__handle.seek(offset, 0)
		self.__handle.write(block)
		self.__completed_blocks.append(block_number)
		ADDON.save_data(self.state_file, {"total_blocks": self.__total_blocks, "completed_blocks": self.__completed_blocks})
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
			if ADDON.get_setting('enable_custom_output') == 'true':
				ADDON.log("Moving %s to %s" % (self.cache_file, self.output_file), LOG_LEVEL.VERBOSE)
				vfs.mv(self.cache_file, self.output_file)
			else:
				vfs.rename(self.cache_file, self.output_file, quiet=True)
		vfs.rm(self.state_file, quiet=True)

class InputHandler():
	def __init__(self, url, raw_url, file_id, total_blocks, total_bytes, headers, completed_blocks = []):
		self.__headers = headers
		self.__streaming = False
		self.__abort = False
		self.__url = url
		self.__file_id = file_id
		self.__block_size = BLOCK_SIZE
		self.__total_blocks = total_blocks
		self.__total_bytes = total_bytes
		self.__completed_blocks = completed_blocks
		self.__output_queue = {}
		self.__cache_file = vfs.join(CACHE_DIRECTORY, self.__file_id + '.temp')
		clear_property('streaming.abort')
	
	def check_abort(self):
		return get_property('streaming.abort')
	
	def is_cached(self, block_number):
		if get_property('streaming.started'): return False
		return block_number in self.__completed_blocks
		
	def read_cached_block(self, block_number):
		f = vfs.open(self.__cache_file, "rb")
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
		block = False
		while attempt < RETRY_ATTEMPTS:
			if self.check_abort(): return False
			if get_property("streaming.seek_block") and block_number < int(get_property("streaming.seek_block")): return False
			attempt += 1
			ADDON.log("block %s attempt %s" % (block_number, attempt), LOG_LEVEL.STANDARD)
			block = self.__call(start_byte, end_byte)
			if block: break
			time.sleep(.25)
		if block: 
			self.__completed_blocks.append(block_number)
		return block
		
	def get_block(self, block_number):
		cached = self.is_cached(block_number)
		#time.sleep(.5)
		if cached:
			ADDON.log("Reading cached block %s" % block_number, LOG_LEVEL.STANDARD)
			return self.read_cached_block(block_number), cached
		else:
			ADDON.log("Reading remote block %s" % block_number, LOG_LEVEL.STANDARD)
			return self.read_remote_block(block_number), cached
		
	def read_block(self, block_number):
		try:
			block = self.__output_queue[block_number]
		except:
			block = False
		return block
	
		#return self.__output_queue.pop(block_number, False)
	
	def save_block(self, block_number, block):
		self.__output_queue[block_number] = block
		
	def __call(self, start_byte, end_byte):
		r = 'bytes=%s-%s' % (start_byte, end_byte)
		#ADDON.log("Requesting remote bytes: %s" % r, LOG_LEVEL.STANDARD)
		try:
			headers = self.__headers
			headers["Range"] = r
			req = urllib2.Request(self.__url, headers=headers)
			f = urllib2.urlopen(req, timeout=2)
			if f.getcode() != 206: return False
			change_thread_count(1)
			block = ''
			while True:
				if self.check_abort(): return False
				bite = f.read(FRAME_SIZE)
				if not bite: break
				block += bite
			f.close()
			change_thread_count(-1)
		except Exception, e:
			ADDON.log("HTTP Error: %s" % e, LOG_LEVEL.VERBOSE)
			return False
		return block
		
class Transmogrifier():
	def __init__(self, id, url, raw_url, filename, file_id, video_type='tvshow', save_dir=False):
		self.win = xbmcgui.Window(10000)
		self.threads = NUMBER_THREADS
		self.block_size = BLOCK_SIZE
		self.total_bytes = 0
		self.total_blocks = 0
		self.cached_bytes = 0
		self.cached_blocks = 0
		self.total_bytes = False
		self.id = id
		self.url = url
		self.filename = filename
		self.raw_url = raw_url
		self.file_id = file_id
		self.save_dir = save_dir
		self.video_type = video_type
		self.Pool = ThreadPool(NUMBER_THREADS)
		self.completed = []
		self.__aborting = False
		self.set_headers(url)
		set_thread_count(0)
	
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
			clear_property("caching.file_id")
			clear_property(self.file_id +'.status')
			clear_property('streaming.abort')
			clear_property('streaming.tail_requested')
			ADDON.log("Aborting Transmogrification...", LOG_LEVEL.VERBOSE)
			ADDON.log("Cleaning Cache...", LOG_LEVEL.VERBOSE)
			ADDON.log("Waiting to Transmogrify...", LOG_LEVEL.VERBOSE)
			self.__aborting = True
		
	def transmogrify(self, block_number):
		if get_property("streaming.seek_block"):
			if block_number < int(get_property("streaming.seek_block")): 
				return [True, block_number]
		if self.check_abort(): 
			ADDON.log("Abort All", LOG_LEVEL.STANDARD)
			self.abort_all()
			return False
		block, cached = self.Input.get_block(block_number)
		if not block: 
			return [False, block_number]

		if self.video_type == 'stream':
			self.Input.save_block(block_number, block)
			self.cached_bytes += len(block)
			percent, delta, kbs = self.calculate_progress()
			set_property(self.file_id +'.status', json.dumps({'id': self.id, 'total_bytes': self.total_bytes, 'cached_bytes': self.cached_bytes, 'speed': kbs}))
			ADDON.log("Streaming Progress: %s/%s %s KBs" % (self.cached_bytes, self.total_bytes, kbs), LOG_LEVEL.STANDARD)
		else:
			offset_byte = block_number * self.block_size
			self.Output.queue_block(block, offset_byte, block_number)
			self.cached_bytes += len(block)
			percent, delta, kbs = self.calculate_progress()
			self.cached_blocks += 1
			set_property(self.file_id +'.status', json.dumps({'id': self.id, 'total_bytes': self.total_bytes, 'cached_bytes': self.cached_bytes, 'cached_blocks': self.cached_blocks, 'total_blocks': self.total_blocks, 'percent': percent, 'speed': kbs, 'active_threads': get_property("active_threads")}))
			ADDON.log("Caching Progress: %s%s %s/%s %s KBs" % (percent, '%', self.cached_bytes, self.total_bytes, kbs), LOG_LEVEL.STANDARD)
		return [True, block_number]
			
			
	def transmogrified(self, result):
		if self.check_abort(): 
			self.abort_all()
			return False
		status = result[0]
		block_number = result[1]
		if status is False and not get_property('streaming.abort'):
			if get_property("streaming.seek_block") and block_number < int(get_property("streaming.seek_block")): return
			ADDON.log("Requeue %s" % block_number, LOG_LEVEL.STANDARD)
			self.Pool.queueTask(self.transmogrify, block_number, block_number, self.transmogrified)

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
			self.state_file = vfs.join(WORK_DIRECTORY, self.file_id + '.state')
			completed_blocks = []
			if vfs.exists(self.state_file):
				temp = ADDON.load_data(self.state_file)
				if int(temp['total_blocks']) == self.total_blocks:
					completed_blocks = temp['completed_blocks']
			self.Output = OutputHandler(self.video_type, self.filename, self.file_id, self.total_blocks, completed_blocks=completed_blocks, extension=self.extension, save_dir=self.save_dir)
			self.Input = InputHandler(self.url, self.raw_url, self.file_id, self.total_blocks, self.total_bytes, self.__headers, completed_blocks=completed_blocks)
			self.processor = Thread(target=self.Output.process_queue)
			self.processor.start()
			self.started = time.time()
			self.cached_bytes = 0
			for block_number in range(0, self.total_blocks+1):
				self.Pool.queueTask(self.transmogrify, block_number, block_number, self.transmogrified)

			
			self.processor.join()
			self.Pool.joinAll()
			percent, delta, kbs = self.calculate_progress()
			clear_property(self.file_id +'.status')
			message = 'Completed %s in %s second(s) at %s KB/s.' % (self.filename, delta, kbs)
			ADDON.log(message, LOG_LEVEL.VERBOSE)
			ADDON.raise_notify(ADDON_NAME, message)
		else:
			ADDON.log('Invalid url, sorry!', LOG_LEVEL.VERBOSE)
			ADDON.raise_notify(ADDON_NAME, "Unable to download source, try another")
		
	def stream(self, start_byte=0):
		first_block = self.get_block_number_from_byte(start_byte)
		self.Input = InputHandler(self.url, self.raw_url, self.file_id, self.total_blocks, self.total_bytes, self.__headers)
		self.Input.__streaming = True
		self.started = time.time()
		self.cached_bytes = 0
		for block_number in range(first_block, self.total_blocks+1):
			self.Pool.queueTask(self.transmogrify, block_number, block_number, self.transmogrified)
		return True

	def seek(self, start_byte):
		ADDON.log("Seek to byte %s " % start_byte, LOG_LEVEL.VERBOSE)
		first_block = self.get_block_number_from_byte(start_byte)
		ADDON.log("Seek to block %s " % first_block, LOG_LEVEL.VERBOSE)
		set_property("streaming.seek_block", str(first_block))

		set_property('streaming.abort', 'true')
		self.Pool.emptyQueue()
		time.sleep(.25)

		self.Input = InputHandler(self.url, self.raw_url, self.file_id, self.total_blocks, self.total_bytes, self.__headers)
		self.Input.__streaming = True
		self.started = time.time()
		for block_number in range(first_block, self.total_blocks+1):
			self.Pool.queueTask(self.transmogrify, block_number, block_number, self.transmogrified)
	
	def get_last_byte(self, last_byte):
		''''r = 'bytes=%s-' % last_byte
		set_property('streaming.abort', 'true')
		while True:
			if self.check_abort(): return False
			try:
				headers = self.__headers
				headers["Range"] = r
				req = urllib2.Request(self.url, headers=headers)
				f = urllib2.urlopen(req, timeout=2)
				last_byte = f.read()
				f.close()
				if last_byte:
					clear_property('streaming.abort')
					return last_byte
			except:
				pass
			time.sleep(.1)
		'''
		pass
		
	def read_block(self, start_byte=0):
		end_byte = (start_byte + self.block_size) - 1
		if end_byte > self.total_bytes: end_byte = self.total_bytes
		block_number = self.get_block_number_from_byte(start_byte)
		block = self.Input.read_block(block_number)
		if block:
			return block, end_byte, block_number
		else:
			return False, start_byte, block_number

	def get_block_number_from_byte(self, start_byte):
		block_number = int(math.floor(float(start_byte) / self.block_size))
		return block_number

	def request_tail_bytes(self):
		tail_bytes = ''
		self.tail_file = vfs.join(WORK_DIRECTORY, self.file_id + '.tail')
		if not get_property('streaming.tail_requested'):
			ADDON.log("Requesting Remote Tail Bytes")
			out_f = open(self.tail_file, 'wb')
			tail_byte = self.total_bytes - 65536
			r = 'bytes=%s-' % tail_byte
			headers = self.__headers
			headers["Range"] = r
			req = urllib2.Request(self.url, headers=headers)
			in_f = urllib2.urlopen(req, timeout=2)
			tail_bytes = in_f.read()
			out_f.write( tail_bytes )
			in_f.close()
			out_f.close()
			set_property('streaming.tail_requested', 'true')
		else:
			ADDON.log("Reading Cached Tail Bytes")
			in_f = open(self.tail_file, 'rb')
			tail_bytes = in_f.read()
			in_f.close()
		return tail_bytes
	
	def get_tail_bytes(self):
		tail_bytes = self.request_tail_bytes()
		
	def get_target_info(self):
		table = {
			"application/x-troff-msvideo":		"avi",
			"video/avi":						"avi",
			"video/msvideo":					"avi",
			"video/x-msvideo":					"avi",
			"video/quicktime":					"mov",
			"video/mp4":						"mp4",
			"video/x-matroska":					"mkv",
			"video/flv":						"flv",
			"video/x-flv":						"flv"
		}
		try:
			req = urllib2.Request(self.url, headers=self.__headers)
			self.net = urllib2.urlopen(req, timeout=3)
			self.headers = self.net.headers.items()
			try:
				self.total_bytes = int(self.net.headers["Content-Length"])
				self.total_blocks = int(math.ceil(self.total_bytes / self.block_size))
			except: return False
			ADDON.log("Total blocks: %s" % self.total_blocks, LOG_LEVEL.VERBOSE)
			self.extension = False
			try:
				self.extension = re.search('filename="(.+?)\.(mkv|avi|mov|mp4|flv)"$', self.net.headers["Content-Disposition"], re.IGNORECASE).group(2).lower()
			except:pass
			if not self.extension:
				try:
					ADDON.log("Found content-type: %s" % self.net.headers["Content-Type"], LOG_LEVEL.VERBOSE)
					self.extension = table[self.net.headers["Content-Type"]]
				except:
					ADDON.log("No content-type found, assuming avi", LOG_LEVEL.VERBOSE)
					self.extension = 'avi'
			set_property(self.file_id +'.status', json.dumps({'id': self.id, 'total_bytes': self.total_bytes, 'cached_bytes': self.cached_bytes, 'cached_blocks': 0, 'total_blocks': self.total_blocks, 'percent': 0, 'speed': 0}))
		
			if self.video_type == 'stream':
				self.request_tail_bytes()
		
		except urllib2.URLError, e:
			ADDON.log("HTTP Error: %s" % e, LOG_LEVEL.VERBOSE)
			ADDON.raise_notify("%s ERROR" % ADDON_NAME, "Unable to open URL","HTTP Error: %s" % e)
			return False
		if self.total_bytes is False :
			return False
		return True		