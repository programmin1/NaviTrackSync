#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Luke's Navicomputer Sync
# Should sync gpx files for any computer, not just Windows.

import time
import BaseHTTPServer
import SocketServer
import urllib
import socket
import sys

#from pprint import pprint
import urlparse
import os
import re

HOST_NAME = ''
PORT_NUMBER = 80

import socket

#See http://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
if os.name != "nt":
    import fcntl
    import struct

    def get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s',
                                ifname[:15]))[20:24])

def get_lan_ip():
    ip = socket.gethostbyname(socket.gethostname())
    if ip.startswith("127.") and os.name != "nt":
        interfaces = [
            "eth0",
            "eth1",
            "eth2",
            "wlan0",
            "wlan1",
            "wifi0",
            "ath0",
            "ath1",
            "ppp0",
            ]
        for ifname in interfaces:
            try:
                ip = get_interface_ip(ifname)
                break
            except IOError:
                pass
    return ip


def getLatestTime( gpxfile ):
    import xml.etree.ElementTree as ET
    import time
    import datetime
    
    tree = ET.parse( gpxfile )
    root = tree.getroot()
    #elements are {http://www.topografix.com/GPX/1/1}TAGNAME so adjust, find time:
    newestTime = 0
    for t in root.iter( root.tag.replace('gpx','time') ):
	timestr = t.text
	dt = datetime.datetime.strptime( timestr, "%Y-%m-%dT%H:%M:%SZ")
	timeNum = time.mktime( dt.timetuple() )
	if timeNum > newestTime:
	    newestTime = timeNum
    if newestTime == 0:
	raise ValueError
    
    return newestTime
	

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	"""
		Core of the sync process - handle requests for files to send, 
		download files phone wants to sync.
	"""
	def do_GET(s):
		"""Respond to a GET request."""
		print "GET", s.path
		if s.path.startswith('/downloadlist.txt'):
			list = ""
			for item in gpxs:
				list += item + "\r\n"
			print list
			s.send_response(200)
			s.send_header("Content-type", "text/plain")
			s.send_header("Content-Length", len(list))
			s.end_headers()
			s.wfile.write(list)
		elif re.match('/(.*)\.gpx', s.path):
			#Again, clean in case of sneaky /some/other/files
			fileread = urllib.unquote(re.match('/(.*)\.gpx', s.path).group(0)).replace(os.sep,'')
			print "file ", fileread
			contents = file(fileread).read()
			if len(contents) >1:
				print 'sending.'
				s.send_response(200)
				s.send_header("Content-type", "application/octet-stream")
				s.end_headers()
				#print file(fileread).read()
				s.wfile.write(contents)
		else:
			s.send_response(200)
			s.send_header("Content-type", "text/plain")
			s.end_headers()
			s.wfile.write("")

	def do_POST(s):
		gpx = s.rfile.read(int(s.headers['content-length']))
		s.send_response(200)
		s.send_header("Content-type", "text/html")
		s.end_headers()
		if s.path.startswith('/?'):
			query = urlparse.parse_qs(s.path[2:])
			if (query.has_key('filename')):
				# Replace / in case it's something sneaky
				filename = query['filename'][0].replace(os.sep, '')
				print "Receiving", filename
				# Receive the file POST, write to filename:
				with open(filename, 'w') as gpxfile:
				    gpxfile.write( gpx )
				print 'Downloaded', filename
				#Set file time to the time the file is, not all just the time downloaded:
				with open(filename, 'r') as gpxfile:
				    lastTS = getLatestTime(gpxfile)
				    os.utime( filename, (lastTS, lastTS) )
				
		#pprint(vars(s));

class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
	""" Threaded http server """
	

if __name__ == '__main__':
	
	gpxs = [gpx for gpx in os.listdir(os.curdir) if (gpx.endswith('.gpx') and os.path.getsize(gpx) >1) ]
	if len(gpxs):
		print "The following will be sent to device:"
		print gpxs
		
	print "Set Navicomputer sync to", get_lan_ip(), "to sync gpx."
	
	# Two different serving methods. Threaded should be faster:
    #server_class = BaseHTTPServer.HTTPServer
	server_class = ThreadedHTTPServer;
	try:
		httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
	except socket.error:
		print "Could not bind port 80 - is Apache using it? Are you sure you're sudo/adminsitrator?"
		sys.exit()
	print time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER)
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	httpd.server_close()
	print time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER)
