import json
import xbmcgui
from dudehere.routines import *
from dudehere.routines.vfs import VFSClass
vfs = VFSClass()
AUTH_PIN = ADDON.get_setting('auth_pin')

NUMBER_THREADS = int(ADDON.get_setting('thread_number'))
if ADDON.get_setting('enable_custom_work') == "true":
	WORK_DIRECTORY = ADDON.get_setting('work_directory')
else:
	WORK_DIRECTORY = vfs.join(DATA_PATH, 'work')

if ADDON.get_setting('enable_custom_output') == "true":
	CACHE_DIRECTORY = ADDON.get_setting('save_directory')
else:
	CACHE_DIRECTORY = vfs.join(DATA_PATH, 'downloads')

MOVIE_DIRECTORY = vfs.join(CACHE_DIRECTORY, 'Movies')
TVSHOW_DIRECTORY = vfs.join(CACHE_DIRECTORY, 'TV Shows')

BLOCK_SIZE = int(float(ADDON.get_setting('block_size')) * 1024 * 1024)
RETRY_ATTEMPTS = int(ADDON.get_setting('retry_attempts'))

WINDOW_PREFIX = 'transmogrifier'
WEB_ROOT = vfs.join(ROOT_PATH, 'resources/www/html')
CONTROL_PORT = int(ADDON.get_setting('control_port'))
VALID_TOKENS = []

ADDON.log("Work Directory: %s" % WORK_DIRECTORY)
ADDON.log("Cache Directory: %s" % CACHE_DIRECTORY)
if not vfs.exists(DATA_PATH): vfs.mkdir(DATA_PATH)
if not vfs.exists(CACHE_DIRECTORY): vfs.mkdir(CACHE_DIRECTORY)
if not vfs.exists(WORK_DIRECTORY): vfs.mkdir(WORK_DIRECTORY)
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
