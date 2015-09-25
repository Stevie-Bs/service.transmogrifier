import json
import xbmcgui
from dudehere.routines import *
from dudehere.routines.vfs import VFSClass
vfs = VFSClass()
AUTH_PIN = ADDON.get_setting('auth_pin')

NUMBER_THREADS = int(ADDON.get_setting('thread_number'))
CACHE_DIRECTORY = ADDON.get_setting('save_directory')
MOVIE_DIRECTORY = vfs.join(CACHE_DIRECTORY, 'Movies')
TVSHOW_DIRECTORY = vfs.join(CACHE_DIRECTORY, 'TV Shows')
BLOCK_SIZE = 1024 * 2000

WINDOW_PREFIX = 'transmogrifier'
WEB_ROOT = vfs.join(ROOT_PATH, 'resources/www/html')
CONTROL_PORT = int(ADDON.get_setting('control_port'))
VALID_TOKENS = []

ADDON.log("Cache Directory: %s" % CACHE_DIRECTORY)
if not vfs.exists(DATA_PATH): vfs.mkdir(DATA_PATH)
if not vfs.exists(CACHE_DIRECTORY): vfs.mkdir(CACHE_DIRECTORY)
if not vfs.exists(MOVIE_DIRECTORY): vfs.mkdir(MOVIE_DIRECTORY)
if not vfs.exists(TVSHOW_DIRECTORY): vfs.mkdir(TVSHOW_DIRECTORY)

def set_property(k, v):
	k = "%s.%s" % (WINDOW_PREFIX, k)
	xbmcgui.Window(10000).setProperty(k, str(v))
	
def get_property(k):
	k = "%s.%s" % (WINDOW_PREFIX, k)
	p = xbmcgui.Window(10000).getProperty(k)
	if p == 'false': return False
	if p == 'true': return True
	return p

def clear_property(k):
	k = "%s.%s" % (WINDOW_PREFIX, k)
	xbmcgui.Window(10000).clearProperty(k)