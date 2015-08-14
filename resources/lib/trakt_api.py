import urllib2, urllib
from urllib2 import URLError, HTTPError
from common import *
from datetime import datetime
import re, time
try: 
	import simplejson as json
except ImportError: 
	import json
CLIENT_ID = "7fe0eea41783130c7c3c3c0a99153740e19964bcd84cc488ef0691881e2c5da9"
SECRET_ID = "d0858eff6524270fc1e5dfb6e32583b22aa1111cf5d097214b54f74cc207cce0"
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
BASE_URL = "https://api-v2launch.trakt.tv"
PIN_URL = "http://trakt.tv/pin/4428"
DAYS_TO_GET = 21
DECAY = 2

class TraktAPI():
	def __init__(self, token="", quiet=False):
		self.quiet = quiet
		self.token = token
	
	def search(self, query, media='show'):
		uri = '/search'
		results =  self._call(uri, params={'query': query, 'type': media})
		return results
		
	def get_show_seasons(self, imdb_id):
		uri = '/shows/%s/seasons' % imdb_id
		return self._call(uri, params={'extended': 'images'})
	
	def get_show_episodes(self, imdb_id, season):
		uri = '/shows/%s/seasons/%s' % (imdb_id, season)
		media='episode'
		return self._process_records(self._call(uri, params={'extended': 'full,images'}, cache=media), media)
	
	def get_episode_screenshot(self, imdb_id, season, episode):
		uri = '/shows/%s/seasons/%s/episodes/%s' %(imdb_id, season, episode)
		response = self._call(uri, params={'extended': 'images'})
		return response['images']['screenshot']['full']
	
	def get_show_info(self, imdb_id, episodes=False):
		if episodes:
			uri = '/shows/%s/seasons' % imdb_id
			return self._call(uri, params={'extended': 'episodes,full'})
		else:
			uri = '/shows/%s' % imdb_id
			return self._call(uri)
	
	def get_movie_info(self, imdb_id):
		uri = '/movies/%s' % imdb_id
		return self._call(uri, params={})
	
	def get_episode_info(self, imdb_id, season, episode):
		uri = '/shows/%s/seasons/%s/episodes/%s' % (imdb_id, season, episode)
		response = self._call(uri, params={'extended': 'images'})
		

	def _call(self, uri, data=None, params=None):
		json_data = json.dumps(data) if data else None
		headers = {'Content-Type': 'application/json', 'trakt-api-key': CLIENT_ID, 'trakt-api-version': 2}
		url = '%s%s' % (BASE_URL, uri)
		if params:
			params['limit'] = 100
		else:
			params = {'limit': 100}
		url = url + '?' + urllib.urlencode(params)
		try:
			request = urllib2.Request(url, data=json_data, headers=headers)
			f = urllib2.urlopen(request)
			result = f.read()
			response = json.loads(result)
		except HTTPError as e:
			ADDON.log(url)
			ADDON.log(headers)
			error_msg = 'Trakt HTTP Error %s: %s' % ( e.code, e.reason)
			if self.quiet ==False:
				ADDON.show_error_dialog([error_msg])
		except URLError as e:
			ADDON.log(url)
			error_msg = 'Trakt URL Error %s: %s' % ( e.code, e.reason)
			if self.quiet ==False:
				ADDON.show_error_dialog([error_msg])
		else:
			return response
	