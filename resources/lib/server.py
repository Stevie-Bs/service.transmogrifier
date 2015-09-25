import json
import cgi
import re
import hashlib
import time
import uuid
import base64
from os import curdir, sep
from urlparse import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler
from dudehere.routines import *
from dudehere.routines.vfs import VFSClass
from resources.lib.common import *
from resources.lib.database import *
from resources.lib.transmogrifier import OutputHandler, Transmogrifier
from Cookie import SimpleCookie
vfs = VFSClass()

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
	def process_cgi(self):
		parts = urlparse(self.path)
		path = parts.path
		query = parts.query
		data = cgi.parse_qs(query, keep_blank_values=True)
		arguments = path.split('/')
		return arguments, data, path
	
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
		arguments, data, path = self.process_cgi()
		self.send_response(200)
		self.send_header("Content-Type", "video/mp4")
		self.send_header("Accept-Ranges","bytes")
		file_id = arguments[3]
		self.send_header("Set-Cookie", "file_id=" + file_id)
		self.end_headers()

	
	def do_GET(self):
		arguments, data, path = self.process_cgi()
		print self.headers
		cookies = {}
		if 'cookie' in self.headers:
			cookies = {e.split('=')[0]: e.split('=')[1] for e in self.headers['cookie'].split(';')}
		try:
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
				#if 'file_id' in cookies:
				#	file_id = cookies['file_id']
				self.send_response(206)
				self.send_header("Pragma", "no-cache")
				self.send_header("Last-Modified","Wed, 21 Feb 2000 08:43:39 GMT")
				self.send_header("Expires", "0")
				self.send_header("ETag",file_id)
				self.send_header("Accept-Ranges","bytes")
				self.send_header("Cache-Control","public, must-revalidate")
				self.send_header("Cache-Control","no-cache")
				self.send_header("Content-Type", "video/video/mp4")
				self.send_header("Features","seekable,stridable")
				self.send_header("Connection", 'close')
				self.send_header("client-id","12345")
				self.send_header("Content-Disposition", 'inline; filename="stream.mp4"')
				self.send_header("Set-Cookie", "file_id=" + file_id)
				TM = Transmogrifier(url, '', '', file_id, video_type='stream')
				TM.get_target_info()
				file_size = TM.total_bytes
				current_byte = 0
				try:
					range_reqeust = str(self.headers.getheader("Range"))
					temp=range_reqeust.split("=")[1].split("-")
					current_byte=int(temp[0])
					end_byte = file_size - 1 if temp[1] == "" else temp[1]
				except:
					current_byte = 0
					end_byte = file_size - 1
				content_range = "%s-%s/%s" % (current_byte, end_byte, file_size)
				print content_range
				self.send_header("Content-Length", str(file_size))
				self.send_header("Content-Range",content_range)
				self.end_headers()
				
				if not get_property("stream_started"):
					TM.stream()
					set_property("stream_started", "true")
				else:
					TM.seek()
				while True:
					try:
						block, end_byte = TM.read_block(start_byte=current_byte)
						if block is not False:
							current_byte = end_byte + 1
							self.wfile.write(block)
							if end_byte >= file_size:
								break
						else:
							time.sleep(.1)
					except Exception, e:
						print e
						break
				del TM
					#self.wfile.close()
		
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
		except IOError:
			self.send_error(500,'Internal Server Error')
			self.wfile.close()
			return False
		self.wfile.close()
		
	def do_POST(self):
		parts = urlparse(self.path)
		#try:
		path = parts.path
		if path == '/api.json':
			query = parts.query
			params = cgi.parse_qs(query, keep_blank_values=True)
			self.data_string = self.rfile.read(int(self.headers['Content-Length']))
			data = json.loads(self.data_string)
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
			
			if data['token'] not in VALID_TOKENS:
				self.send_error(401,'Unauthorized')
				return

			if data['method'] == 'enqueue':
				try:
					count = len(data['videos'])
					SQL = "INSERT INTO queue(video_type, filename, raw_url, url) VALUES(?,?,?,?)"
					inserts =[]
					for video in data['videos']:
						raw_url = video['raw_url']
						url = video['url']
						if 'resolve' in video.keys():
							if video['resolve'] == 'true':
								raw_url = video['url']
								url = ''
						inserts.append((video['type'], video['filename'], raw_url, url))
					print inserts	
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
				try:
					progress = {
							"id": get_property('id'), 
							"cached_bytes": get_property('cached_bytes'),
							"total_bytes": get_property('total_bytes'),
							"percent": get_property('percent'),
							"active_threads": get_property('active_threads'),
							"speed": get_property('speed'),
					}
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method'], 'progress': progress})
				except:
						self.send_error(500,'Internal Server Error')		
			elif data['method'] == 'queue':
					try:
						DB=MyDatabaseAPI(DB_FILE)
						rows = DB.query("SELECT id, video_type, filename, status, raw_url FROM queue ORDER BY id ASC", force_double_array=True)
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
					set_property("abort_all", "true")
					self.do_Response({'status': 200, 'message': 'success', 'method': data['method']})
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