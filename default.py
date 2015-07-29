#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
sys.path.append(os.path.join(xbmc.translatePath( "special://home/addons/script.module.pyxbmctmanager/" ), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
from common import *
from database import *
from vfs import VFSClass
vfs = VFSClass()
DB_FILE = vfs.join(DATA_PATH, 'cache.db')
DB=SQLiteDatabase(DB_FILE)


def add_to_queue():
	SQL = "INSERT INTO queue(video_type, filename, raw_url, url) VALUES(?,?,?,?)"
	DB.execute(SQL, [args['video_type'], args['filename'], args['raw_url'], args['resolved_url']])
	DB.commit()


args = ADDON.parse_query(sys.argv[2])
print args
if args['mode'] == 		'main':
	print "blah"
elif args['mode'] ==	'add_to_queue':
	add_to_queue()	