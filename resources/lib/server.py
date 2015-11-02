import json
import sys
import cgi
import re
import hashlib
import time
import base64
import datetime
import socket
from os import curdir, sep
from urlparse import urlparse
from SocketServer import ThreadingMixIn
from BaseHTTPServer import BaseHTTPRequestHandler
from dudehere.routines import *
from dudehere.routines.vfs import VFSClass
from resources.lib.common import *
from resources.lib.database import *
from resources.lib.transmogrifier import OutputHandler, Transmogrifier
vfs = VFSClass()
LOG_FILE = vfs.join(DATA_PATH, 'access.log')
ADDON.log("Setting Access log to: %s" % LOG_FILE)

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

	log_file = vfs.open(LOG_FILE, 'w')
	def process_cgi(self):
		parts = urlparse(self.path)
		path = parts.path
		query = parts.query
		data = cgi.parse_qs(query, keep_blank_values=True)
		arguments = path.split('/')
		return arguments, data, path

	def finish(self,*args,**kw):
		try:
			if not self.wfile.closed:
				self.wfile.flush()
				self.wfile.close()
		except socket.error:
			pass
		self.rfile.close()
	
	def handle(self):
		"""Handles a request ignoring dropped connections."""
		try:
			return BaseHTTPRequestHandler.handle(self)
		except (socket.error, socket.timeout) as e:
			self.connection_dropped(e)

	def connection_dropped(self, error, environ=None):
		print "kodi disconnected"

	def log_message(self, format, *args):
		self.log_file.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format%args))
	
	def _send_response(self, content, code=200, mime="application/json", headers=None):
		self.send_response(code)
		self.send_header('Content-type',	mime)
		if headers is not None:
			for header_type, header in headers:
				self.send_header(header_type, header)
		self.end_headers()
		if mime == 'application/json':
			content = json.dumps(content)
		self.wfile.write(content)
		self.wfile.flush()
	
	def do_HEAD(self):
		print str(self.headers)
		arguments, data, path = self.process_cgi()
		file_id =  arguments[3]
		if get_property("streaming.file_id") != file_id:
			set_property("streaming.file_id", file_id)
			streaming_url = base64.b64decode(arguments[2])
			set_property("streaming.url", streaming_url)
			TM = Transmogrifier(0, get_property("streaming.url"), '', 'stream.avi', get_property("streaming.file_id"), video_type='stream')
			TM.get_target_info()
			set_property("streaming.total_bytes", TM.total_bytes)
			set_property("streaming.total_blocks", TM.total_blocks)
			del TM

		total_bytes = int(get_property("streaming.total_bytes"))
		self.generate_respose_headers()
		self._response_headers['Content-Length'] = total_bytes
		self.send_response(200)
		for header in self._response_headers.keys():
			self.send_header(header, self._response_headers[header])
		self.end_headers()
	
	def generate_respose_headers(self):
		self._response_headers = {}
		now = datetime.datetime.utcnow()
		self._response_headers['Date'] = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
		self._response_headers['Server'] = 'Transmogrifier'
		self._response_headers['Last-Modified'] = "Wed, 21 Feb 2000 08:43:39 GMT"
		self._response_headers['ETag'] = get_property("streaming.file_id")
		self._response_headers['Accept-Ranges'] = 'bytes'
		self._response_headers['Content-Length'] = 0
		self._response_headers['Content-Type'] = "video/x-msvideo"

	
	def do_GET(self):
		arguments, data, path = self.process_cgi()
		#print self.headers
		#print arguments
		#print data
		
		
		if True: #try:
			if arguments[1] == 'query':
				if arguments[2] == 'log':
					logfile = vfs.join('special://logpath', 'kodi.log')
					f = vfs.open(logfile)
					contents = f.read()
					f.close()
					contents = re.sub('<host>(.+?)</host>', '<pass>******</pass>', contents)
					contents = re.sub('<name>(.+?)</name>', '<name>******</name>', contents)
					contents = re.sub('<user>(.+?)</user>', '<user>******</user>', contents)
					contents = re.sub('<pass>(.+?)</pass>', '<pass>******</pass>', contents)
					self._send_response(contents, mime="text/plain")
				elif arguments[2] == 'download':
					if data['media'][0] == 'movie':
						path = vfs.join(MOVIE_DIRECTORY, data['file'][0])
					else:
						path = vfs.join(TVSHOW_DIRECTORY, data['file'][0])
					if not vfs.exists(path):
						self.send_error(404,'File Not Found: %s' % self.path)
						return False
					file_size =  vfs.get_size(path)
					f = vfs.open(path, "r")
					
					self.send_response(200)
					self.send_header("Pragma", "public")
					self.send_header("Expires", "0")
					self.send_header("Cache-Control", "must-revalidate, post-check=0, pre-check=0")
					self.send_header("Content-Type", "application/force-download")
					self.send_header("Content-Type", "application/octet-stream")
					self.send_header("Content-Type", "application/download")
					self.send_header("Content-Disposition", 'attachment; filename="%s"' % data['file'][0]);
					self.send_header("Content-Length", file_size)
					self.end_headers()
					self.wfile.write(f.read())
					f.close()
				else:
					self.send_error(400,'Bad Request')
			elif arguments[1] == 'stream':
				hash_url = arguments[2]
				file_id = arguments[3]
				url = base64.b64decode(hash_url)
				self.generate_respose_headers()
				self._response_headers['Content-Length'] = get_property("streaming.total_bytes")
				TM = Transmogrifier(0, get_property("streaming.url"), '', 'stream.avi', get_property("streaming.file_id"), video_type='stream')
				TM.total_bytes = int(get_property("streaming.total_bytes"))
				TM.total_blocks = int(get_property("streaming.total_blocks"))
				current_byte = 0
				ADDON.log(str(self.headers), LOG_LEVEL.VERBOSE)
				try:
					range_reqeust = str(self.headers.getheader("Range"))
					temp=range_reqeust.split("=")[1].split("-")
					current_byte=int(temp[0])
					end_byte = TM.total_bytes - 1 if temp[1] == "" else temp[1]
				except:
					current_byte = 0
					end_byte = TM.total_bytes - 1
				content_range = "%s-%s/%s" % (current_byte, end_byte, TM.total_bytes)
				self._response_headers['Content-Range'] = content_range
				self.send_response(206)
				for header in self._response_headers.keys():
					self.send_header(header, self._response_headers[header])
				self.end_headers()
				if not get_property("streaming.started"):
					set_property("streaming.started", "true")
					ADDON.log("Start streaming at %s bytes" % current_byte, LOG_LEVEL.VERBOSE) 
					TM.stream(current_byte)
				else:
					ADDON.log("Attempt to seek to %s bytes" % current_byte, LOG_LEVEL.VERBOSE) 
					TM.seek(current_byte)
				self.send_video(TM, current_byte, TM.total_bytes)
				
				del TM


		
			else:
				if self.path=='/':
					self.path='/index.html'
				
				fileName, fileExtension = os.path.splitext(self.path)
				headers = {
						'.css': 	'text/css',
						'.js':		'application/javascript',
						'.json':	'application/json',
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
				self.wfile.flush()
				self.wfile.close()
				return True
			return True
		#except IOError:
		#	self.send_error(500,'Internal Server Error')
		#	self.wfile.close()
		#	return False
		self.wfile.close()
		
		
	
	def send_video(self, TM, current_byte, total_bytes):
		while True:
			if get_property("streaming.abort") == 'now':
				set_property("streaming.abort", "")
				break
			try:
				block, end_byte, block_number = TM.read_block(start_byte=current_byte)
				if get_property("streaming.seek_block") and block_number < int(get_property("streaming.seek_block")):
					time.sleep(.1)
				else:
					if block is not False:
						ADDON.log("Proxy %s %s (block, bytes)" % (block_number, end_byte), LOG_LEVEL.VERBOSE) 
						current_byte = end_byte + 1
						self.wfile.write(block)
						if end_byte >= total_bytes:
							break
					else:
						time.sleep(.1)
			except Exception, e:
				print e
				break
		
	def do_POST(self):
		parts = urlparse(self.path)
		#try:
		path = parts.path
		if path == '/api.json':
			query = parts.query
			params = cgi.parse_qs(query, keep_blank_values=True)
			self.data_string = self.rfile.read(int(self.headers['Content-Length']))
			data = json.loads(self.data_string)
			#print self.headers
			#print params
			#print data
			#print VALID_TOKENS
			if data['method'] == 'authorize':
				if str(data['pin']) == ADDON.get_setting('auth_pin'):
					token = hashlib.sha1(str(time.time())).hexdigest()
					VALID_TOKENS.append(token)
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'],'token': token})
					return
				else:
					self.do_Response({'status': 401, 'message': 'Unauthorized', 'method': data['method']})
					return
			elif data['method'] == 'validate_token':
				if data['token'] in VALID_TOKENS: self.do_Response({'status': 200, 'message': 'success', 'method': data['method']})
				else: self.do_Response({'status': 401, 'message': 'Unauthorized', 'method': data['method']})
				return
			'''
			if data['token'] not in VALID_TOKENS:
				self.send_error(401,'Unauthorized')
				return
			'''
			
			if data['method'] == 'enqueue':
				try:
					count = len(data['videos'])
					SQL = "INSERT INTO queue(video_type, filename, save_dir, imdb_id, title, season, episode, raw_url, url, fileid, source_addon) VALUES(?,?,?,?,?,?,?,?,?,?,?)"
					inserts =[]
					for video in data['videos']:
						raw_url = video['raw_url']
						url = video['url']
						file_id = hashlib.md5(url).hexdigest()
						if 'resolve' in video.keys():
							if video['resolve'] == 'true':
								raw_url = video['url']
								url = ''
						save_dir = video['save_dir'] if 'save_dir' in video.keys() else ''
						imdb_id = video['imdb_id'] if 'imdb_id' in video.keys() else ''
						title = video['title'] if 'title' in video.keys() else ''
						season = video['season'] if 'season' in video.keys() else ''
						episode = video['episode'] if 'episode' in video.keys() else ''
						addon = video['addon'] if 'addon' in video.keys() else ''
						inserts.append((video['type'], video['filename'], save_dir, imdb_id, title, season, episode, raw_url, url, file_id, addon))
					DB=MyDatabaseAPI(DB_FILE)
					DB.execute_many(SQL, inserts)
					DB.commit()
					DB.disconnect()
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'],'count': count})
				except:
					self.send_error(500,'Internal Server Error')
			elif data['method'] == 'restart':
				try:
					count = len(data['videos'])
					DB=MyDatabaseAPI(DB_FILE)
					SQL = "UPDATE queue SET status=1 WHERE id=?"
					for video in data['videos']:
						DB.execute(SQL, [video['id']])
					DB.commit()
					DB.disconnect()
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'],'count': count})
				except:
					self.send_error(500,'Internal Server Error')
			elif data['method'] == 'delete':
				try:
					count = len(data['videos'])
					DB=MyDatabaseAPI(DB_FILE)
					SQL = "DELETE FROM queue WHERE id=?"
					for video in data['videos']:
						DB.execute(SQL, [video['id']])
					DB.commit()
					DB.disconnect()
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'],'count': count})
				except:
					self.send_error(500,'Internal Server Error')
			elif data['method'] == 'progress':
				DB=MyDatabaseAPI(DB_FILE, quiet=True)
				queue = DB.query("SELECT id, video_type, filename, status, raw_url, fileid, priority, source_addon FROM queue ORDER BY priority DESC, id", force_double_array=True)
				DB.disconnect()
				try:
					file_id = get_property("caching.file_id")
					progress = json.loads(get_property(file_id +'.status'))
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'], 'progress': progress, 'queue': queue})
				except:
					progress = {'id': 0, 'total_bytes': 0, 'cached_bytes': 0, 'cached_blocks': 0, 'total_blocks': 0, 'percent': 0, 'speed': 0}
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'], 'progress': progress, 'queue': queue})
					#self.send_error(500,'Internal Server Error')		
			elif data['method'] == 'queue':
				try:
					DB=MyDatabaseAPI(DB_FILE)
					rows = DB.query("SELECT id, video_type, filename, status, raw_url, fileid, priority, source_addon FROM queue ORDER BY priority DESC, id", force_double_array=True)
					DB.disconnect()
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'], 'queue': rows})
				except:
					self.send_error(500,'Internal Server Error')
			elif data['method'] == 'tvshows':
				try:
					videos = vfs.ls(TVSHOW_DIRECTORY, pattern="avi$")[1]
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'], 'tvshows': videos})
				except:
					self.send_error(500,'Internal Server Error')
			elif data['method'] == 'movies':
				try:
					videos = vfs.ls(MOVIE_DIRECTORY, pattern="avi$")[1]
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'], 'movies': videos})
				except:
					self.send_error(500,'Internal Server Error')
			elif data['method'] == 'search':
				try:
					from trakt_api import TraktAPI
					trakt = TraktAPI()
					results = trakt.search(data['query'], data['type'])
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'], "results": results})
				except:
					self.send_error(500,'Internal Server Error')
			elif data['method'] == 'abort':
				try:
					DB=MyDatabaseAPI(DB_FILE)
					if 'file_id' in data:
						file_id = data['file_id']
					else:
						
						result = DB.query("SELECT fileid FROM queue WHERE id=?", [data['id']])
						file_id = result[0]
					set_property("abort_id", file_id)
					DB.execute("UPDATE queue SET status=-1 WHERE fileid=?", [file_id])
					DB.commit()
					DB.disconnect()
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'], "file_id": file_id})
				except:
					self.send_error(500,'Internal Server Error')
			else:
				self.send_error(400,'Bad Request')
			
		else:
			self.send_error(403,'Forbidden')
		#except IOError:
		#	self.send_error(500,'Internal Server Error')
		#	return False

			
	def do_Response(self, content={'status': 200, 'message': 'success'}, content_type='application/json', response=200):
		self.send_response(response)
		self.send_header('Content-type',	content_type)
		self.end_headers()
		if content_type == 'application/json':
			content = json.dumps(content)
		self.wfile.write(content)
		self.wfile.flush()
		self.wfile.close()