# $Id$

import sys
import os
import urllib, urlparse
from gtk import *
from gnome.ui import *
from gtkhtml import *
import cStringIO, threading, Queue
import pycurl

# url history
history = []
# links for 'forward'
forward = []
# number of concurrent connections to the web-server
NUM_THREADS = 4


def about(button):
	GnomeAbout('GtkHTML Test with PycURL', '0.0',
		   'May be distributed under the terms of the GPL2',
		   ['Original code by Matt Wilson, modified by Kjetil Jacobsen'],
		   ('This is a useless application demonstrating the\n'
                    'GtkHTML widget with python and PycURL.')).show()

class WorkerThread(threading.Thread):
	def __init__(self, queue, render):
		threading.Thread.__init__(self)
		self.queue = queue
		self.render = render
		
	def run(self):
		while 1:
			url, handle = self.queue.get()
			if url == None:
				raise SystemExit
			b = cStringIO.StringIO()
			curl = pycurl.Curl()
			curl.setopt(pycurl.WRITEFUNCTION, b.write)
			curl.setopt(pycurl.FOLLOWLOCATION, 1)
			curl.setopt(pycurl.MAXREDIRS, 5)
			curl.setopt(pycurl.URL, url)
			try:
				curl.perform()
			except:
				print 'Error retrieving', url
			curl.close()
			self.render.append((b, handle))


class HtmlWindow(GtkHTML):
	def __init__(self):
		GtkHTML.__init__(self)
		self.queue = Queue.Queue()
		self.render = []
		self.threads = []
		for num_threads in range(NUM_THREADS):
			t = WorkerThread(self.queue, self.render)
			t.start()
			self.threads.append(t)

	def mainquit(self, *args):
		for t in self.threads:
			t.queue.put((None, None))
		mainquit()
		
	def load_url(self, html, url):
		self.num_obj = 0
		if history: url = urllib.basejoin(history[-1], url)
		history.append(url)

		html.load_empty()
		handle = html.begin()
		self.request_url(html, url, handle)
		while self.num_obj > 0:
			if len(self.render) == 0:
				mainiteration(0)
				continue
			self.num_obj -= 1
			buf, handle = self.render.pop(0)
			html.write(handle, buf.getvalue())
			html.end(handle, HTML_STREAM_OK)
			buf.close()

	def submit(self, html, method, path, params):
		print 'Submit is not supported yet'
		print method, path, params

	def request_url(self, html, url, handle):
		url = urllib.basejoin(history[-1], url)
		print "Requesting URL: ", url
		self.queue.put((url, handle))
		self.num_obj += 1

	def entry_activate(self, entry, html):
		url = entry.get_text()
		self.load_url(html, url)
		del forward[:]

	def do_back(self, _b):
		forward.append(history[-1])
		del history[-1]
		url = history[-1]
		del history[-1]
		self.load_url(html, url)

	def do_forward(self, _b):
		if len(forward) == 0: return
		self.load_url(html, forward[-1])
		del forward[-1]

	def do_reload(self, _b):
		if len(history) == 0: return
		url = history[-1]
		del history[-1]
		self.load_url(html, url)
	

html = HtmlWindow()

file_menu = [
	UIINFO_ITEM_STOCK('Quit', None, html.mainquit, STOCK_MENU_QUIT),
]
help_menu = [
	UIINFO_ITEM_STOCK('About...', None, about, STOCK_MENU_ABOUT),
]
menus = [
	UIINFO_SUBTREE('File', file_menu),
	UIINFO_SUBTREE('Help', help_menu)
]

toolbar = [
	UIINFO_ITEM_STOCK('Back', 'Previous page', html.do_back, STOCK_PIXMAP_BACK),
	UIINFO_ITEM_STOCK('Forward', 'Next page', html.do_forward,
			  STOCK_PIXMAP_FORWARD),
	UIINFO_ITEM_STOCK('Reload', 'Reload current page', html.do_reload,
			  STOCK_PIXMAP_REFRESH)
]


win = GnomeApp("html_demo", "Python GtkHTML Test")
win.set_wmclass("gtk_html_test", "GtkHTMLTest")
win.connect('delete_event', html.mainquit)

vbox = GtkVBox(spacing=3)
vbox.set_border_width(2)
vbox.show()
win.set_contents(vbox)

entry = GtkEntry()
html.connect('url_requested', html.request_url)
html.connect('link_clicked', html.load_url)
html.connect('submit', html.submit)
entry.connect('activate', html.entry_activate, html)
vbox.pack_start(entry, expand=FALSE)
entry.show()

html.set_usize(800, 600)

sw = GtkScrolledWindow()
sw.set_policy(POLICY_AUTOMATIC, POLICY_AUTOMATIC)
sw.add(html)
vbox.pack_start(sw)

sep = GtkHSeparator()
vbox.pack_start(sep, expand=FALSE)

status = GtkLabel('')
status.set_justify(JUSTIFY_LEFT)
status.set_alignment(0.0, 0.5)
win.set_statusbar(status)
win.create_menus(menus)
win.create_toolbar(toolbar)

html.load_empty()

win.show_all()

threads_enter()
mainloop()
threads_leave()
