# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Exporter Framework - LuxRender Plug-in
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****
#
import time

import bpy

from ef.ef import ef

def LuxLog(*args, popup=False):
	'''
	Send string to EF log, marked as belonging to LuxRender module.
	Accepts variable args (can be used as pylux.errorHandler)
	'''
	if len(args) > 0:
		ef.log(' '.join(['%s'%a for a in args]), module_name='Lux', popup=popup)

# CHOOSE API TYPE
# Write conventional lx* files and use pylux to manage lux process or external process
from ..module import file_api
# Access lux via a remote LuxFire slave
from ..module import luxfire_client
# Access lux only through pylux bindings
from ..module import pure_api

from ef.util.util import TimerThread, format_elapsed_time

class LuxAPIStats(TimerThread):
	'''
	Periodically get lux stats
	'''
	
	KICK_PERIOD = 1
	
	stats_dict = {
		'secElapsed':	   0.0,
		'samplesSec':	   0.0,
		'samplesTotSec':	0.0,
		'samplesPx':		0.0,
		'efficiency':	   0.0,
		#'filmXres':		 0.0,
		#'filmYres':		 0.0,
		#'displayInterval':  0.0,
		'filmEV':		   0.0,
		#'sceneIsReady':	 0.0,
		#'filmIsReady':	  0.0,
		#'terminated':	   0.0,
		#'enoughSamples':	0.0,
	}
	
	stats_format = {
		'secElapsed':		format_elapsed_time,
		'samplesSec':		lambda x: 'Samples/Sec: %0.2f'%x,
		'samplesTotSec':	lambda x: 'Total Samples/Sec: %0.2f'%x,
		'samplesPx':		lambda x: 'Samples/Px: %0.2f'%x,
		'efficiency':		lambda x: 'Efficiency: %0.2f %%'%x,
		'filmEV':			lambda x: 'EV: %0.2f'%x,
		#'sceneIsReady':	lambda x: 'SIR: '+ ('True' if x else 'False'),
		#'filmIsReady':		lambda x: 'FIR: %f'%x,
		#'terminated':		lambda x: 'TERM: %f'%x,
		#'enoughSamples':	lambda x: 'HALT: '+ ('True' if x else 'False'),
	}
	
	stats_string = ''
	
	def stop(self):
		self.active = False
		if self.timer is not None:
			self.timer.cancel()
			
	def kick(self):
		for k in self.stats_dict.keys():
			self.stats_dict[k] = self.LocalStorage['lux_context'].statistics(k)
		
		self.stats_string = ' | '.join(['%s'%self.stats_format[k](v) for k,v in self.stats_dict.items()])
			  
class LuxFilmDisplay(TimerThread):
	'''
	Periodically update render result with Lux's framebuffer
	'''
	def kick(self, render_end=False):
		if self.LocalStorage['RE'] is not None and self.LocalStorage['lux_context'].statistics('sceneIsReady') > 0.0:
			self.LocalStorage['lux_context'].updateFramebuffer()
			px = [] #self.lux_context.framebuffer()
			xres = int(self.LocalStorage['lux_context'].statistics('filmXres'))
			yres = int(self.LocalStorage['lux_context'].statistics('filmYres'))
			if render_end:
				LuxLog('Final render result %ix%i' % (xres,yres))
			else:
				LuxLog('Updating render result %ix%i' % (xres,yres))
			self.LocalStorage['RE'].update_framebuffer(xres,yres,px)

class LuxManager(object):
	'''
	Manage a pylux.Context object for rendering.
	
	Objects of this class are responsible for the life cycle of
	a pylux.Context object, ensuring proper initialisation, usage
	and termination.
	
	Additionally, LuxManager objects will also spawn timer threads
	in order to update the rendering statistics and image framebuffer.
	'''
	
	ActiveManager = None
	@staticmethod
	def SetActive(LM):
		LuxManager.ActiveManager = LM
	@staticmethod
	def ClearActive():
		LuxManager.ActiveManager = None
	
	context_count = 0
	@staticmethod
	def get_context_number():
		'''
		Give each context a unique serial number by keeping
		count in a static member of LuxManager
		'''
		
		LuxManager.context_count += 1
		return LuxManager.context_count
	
	lux_context		= None
	thread_count	= 1
	stats_thread	= None
	fb_thread		= None
	started			= True  # unintuitive, but reset() is called in the constructor !
	
	def __init__(self, manager_name = '', api_type='FILE', threads=1):
		'''
		Initialise the LuxManager by setting its name, the pylux API
		type, and number of threads to render with.
		
		Returns LuxManager object
		'''
		
		self.thread_count = threads
		
		if api_type == 'FILE':
			Context = file_api.Custom_Context
		elif api_type == 'LUXFIRE_CLIENT':
			Context = luxfire_client.Client_Locator
		elif api_type == 'API':
			Context = pure_api.Custom_Context
		else:
			raise Exception('Unknown exporter API type')
		
		if manager_name is not '': manager_name = ' (%s)' % manager_name
		self.lux_context = Context('LuxContext %04i%s' % (LuxManager.get_context_number(), manager_name))
		
		self.reset()

	def start(self, RE):
		'''
		RE			bpy.types.RenderEngine
		
		Start the pylux.Context object rendering. This is achieved
		by calling its worldEnd() method. Here we also start the
		timer threads for stats and framebuffer updates.
		
		Returns None
		'''
		
		if self.started:
			LuxLog('Already rendering!')
			return
		
		self.started = True
		
		# Wait until scene is fully parsed before adding more render threads
		while self.lux_context.statistics('sceneIsReady') != 1.0:
			# TODO: such a tight loop is not a good idea
			time.sleep(0.3)
		
		self.stats_thread.start()
		self.fb_thread.LocalStorage['RE'] = RE
		self.fb_thread.start()
		
		for i in range(self.thread_count - 1):
			self.lux_context.addThread()
	
	def reset(self):
		'''
		Stop the current Context from rendering, and reset the
		timer threads.
		
		Returns None
		'''
		
		# Stop the stats thread
		if self.stats_thread is not None and self.stats_thread.isAlive():
			self.stats_thread.stop()
			self.stats_thread.join()
		
		self.stats_thread  = LuxAPIStats(
			{ 'lux_context': self.lux_context }
		)
		
		if not self.started: return
		self.started = False
		
		self.lux_context.exit()
		self.lux_context.wait()
		
		# Stop the framebuffer update thread
		if self.fb_thread is not None and self.fb_thread.isAlive():
			self.fb_thread.stop()
			self.fb_thread.join()
			# Get the last image
			self.fb_thread.kick(render_end=True)
		
		self.fb_thread  = LuxFilmDisplay(
			{ 'lux_context': self.lux_context }
		)
		
		self.lux_context.cleanup()
		
	def __del__(self):
		'''
		Gracefully exit() lux upon destruction
		'''
		self.reset()
