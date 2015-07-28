import sys
import xbmc
import os
import unicodedata
from addon.common.addon import Addon

ARGS = sys.argv
#print ARGS
try:
	int(ARGS[1])
except:
	ARGS.insert(1, -1)
try: 
	str(ARGS[2])
except:
	ARGS.insert(2, "?/fake")

class MyAddon(Addon):
	def log(self, msg):
		msg = unicodedata.normalize('NFKD', unicode(msg)).encode('ascii','ignore')
		xbmc.log('%s: %s' % (self.get_name(), msg))
	def str2bool(self, v):
		if not v: return False
		return v.lower() in ("yes", "true", "t", "1")
	def get_bool_setting(self, k):
		return(self.str2bool(self.get_setting(k)))
	def raise_error(self, title, message):
		image = self.get_path() + os.sep + 'resources' + os.sep + 'artwork' + os.sep + 'error.jpg'
		xbmc.executebuiltin("XBMC.Notification("+title+","+message+",1500,"+image+")")

ADDON_ID = 'service.transmogrifier'
ADDON_NAME = 'Transmorgifier'
ADDON = MyAddon(ADDON_ID,ARGS)
ADDON_NAME = ADDON.get_name()
VERSION = ADDON.get_version()
ROOT_PATH = ADDON.get_path()
DATA_PATH = ADDON.get_profile()