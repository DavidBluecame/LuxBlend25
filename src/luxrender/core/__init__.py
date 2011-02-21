# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Daniel Genrich
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
"""Main LuxRender extension class definition"""

# System libs
import os
import multiprocessing
import time
import threading
import subprocess
import sys

# Blender libs
import bpy

# Framework libs
from extensions_framework import util as efutil

# Exporter libs
from .. import LuxRenderAddon
from ..export.scene import SceneExporter
from ..outputs import LuxManager, LuxFilmDisplay
from ..outputs import LuxLog
from ..outputs.pure_api import LUXRENDER_VERSION

# Exporter Property Groups need to be imported to ensure initialisation
from ..properties import (
	accelerator, camera, engine, filter, integrator, lamp, material,
	mesh, object as prop_object, sampler, texture, world
)

# Exporter Interface Panels need to be imported to ensure initialisation
from ..ui import (
	render_panels, camera, image, lamps, mesh, object as ui_object, world
)

from ..ui.materials import (
	main, compositing, carpaint, glass, glass2, roughglass, glossytranslucent,
	glossy_lossy, glossy, matte, mattetranslucent, metal, mirror, mix, null,
	scatter, shinymetal, velvet
)

from ..ui.textures import (
	main, band, bilerp, blackbody, brick, cauchy, constant, checkerboard, dots,
	equalenergy, fbm, gaussian, harlequin, imagemap, lampspectrum, luxpop,
	marble, mix, sellmeier, scale, sopra, uv, windy, wrinkled, mapping,
	tabulateddata, transform
)

# Exporter Operators need to be imported to ensure initialisation
from .. import operators
from ..operators import lrmdb

# Add standard Blender Interface elements
import properties_render
properties_render.RENDER_PT_render.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
properties_render.RENDER_PT_dimensions.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
properties_render.RENDER_PT_output.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
del properties_render

import properties_material
properties_material.MATERIAL_PT_context_material.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
properties_material.MATERIAL_PT_preview.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
del properties_material

import properties_data_lamp
properties_data_lamp.DATA_PT_context_lamp.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
# properties_data_lamp.DATA_PT_area.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
del properties_data_lamp

@classmethod
def blender_texture_poll(cls, context):
	tex = context.texture
	show = tex and \
		   ((tex.type == cls.tex_type and not tex.use_nodes) and \
		   (context.scene.render.engine in cls.COMPAT_ENGINES))
	
	if context.scene.render.engine == LuxRenderAddon.BL_IDNAME:
		show = show and tex.luxrender_texture.type == 'BLENDER'
	
	return show

import properties_texture
properties_texture.TEXTURE_PT_context_texture.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
# properties_texture.TEXTURE_PT_preview.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
blender_texture_ui_list = [
	properties_texture.TEXTURE_PT_blend,
	properties_texture.TEXTURE_PT_clouds,
	properties_texture.TEXTURE_PT_distortednoise,
	properties_texture.TEXTURE_PT_image,
	properties_texture.TEXTURE_PT_magic,
	properties_texture.TEXTURE_PT_marble,
	properties_texture.TEXTURE_PT_musgrave,
	#properties_texture.TEXTURE_PT_noise,
	properties_texture.TEXTURE_PT_stucci,
	properties_texture.TEXTURE_PT_voronoi,
	properties_texture.TEXTURE_PT_wood,
]
for blender_texture_ui in blender_texture_ui_list:
	blender_texture_ui.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
	blender_texture_ui.poll = blender_texture_poll

del properties_texture

# compatible() copied from blender repository (netrender)
def compatible(mod):
	mod = __import__(mod)
	for subclass in mod.__dict__.values():
		try:
			subclass.COMPAT_ENGINES.add(LuxRenderAddon.BL_IDNAME)
		except:
			pass
	del mod

compatible("properties_data_mesh")
compatible("properties_data_camera")
compatible("properties_particle")

@LuxRenderAddon.addon_register_class
class RENDERENGINE_luxrender(bpy.types.RenderEngine):
	'''
	LuxRender Engine Exporter/Integration class
	'''
	
	bl_idname			= LuxRenderAddon.BL_IDNAME
	bl_label			= 'LuxRender'
	bl_use_preview		= True
	
	render_lock = threading.Lock()
	
	def render(self, scene):
		'''
		scene:	bpy.types.Scene
		
		Export the given scene to LuxRender.
		Choose from one of several methods depending on what needs to be rendered.
		
		Returns None
		'''
		
		with RENDERENGINE_luxrender.render_lock:	# just render one thing at a time
			
			self.LuxManager				= None
			self.render_update_timer	= None
			self.output_dir				= efutil.temp_directory()
			self.output_file			= 'default.png'
			
			prev_dir = os.getcwd()
			
			if scene is None:
				LuxLog('ERROR: Scene to render is not valid')
				return
			
			if scene.name == 'preview':
				self.render_preview(scene)
				return
			
			if scene.render.use_color_management == False:
				LuxLog('WARNING: Colour Management is switched off, render results may look too dark.')
			
			if self.render_scene(scene) == False:
				return
			
			self.render_start(scene)
			os.chdir(prev_dir)
	
	def render_preview(self, scene):
		self.output_dir = efutil.temp_directory()
		
		if self.output_dir[-1] != '/':
			self.output_dir += '/'
		
		efutil.export_path = self.output_dir
		#print('(2) export_path is %s' % efutil.export_path)
		os.chdir( self.output_dir )
		
		from ..outputs.pure_api import PYLUX_AVAILABLE
		if not PYLUX_AVAILABLE:
			self.bl_use_preview = False
			LuxLog('ERROR: Material previews require pylux')
			return
		
		from ..export import materials as export_materials
		
		# Iterate through the preview scene, finding objects with materials attached
		objects_mats = {}
		for obj in [ob for ob in scene.objects if ob.is_visible(scene) and not ob.hide_render]:
			for mat in export_materials.get_instance_materials(obj):
				if mat is not None:
					if not obj.name in objects_mats.keys(): objects_mats[obj] = []
					objects_mats[obj].append(mat)
		
		PREVIEW_TYPE = None		# 'MATERIAL' or 'TEXTURE'
		
		# find objects that are likely to be the preview objects
		preview_objects = [o for o in objects_mats.keys() if o.name.startswith('preview')]
		if len(preview_objects) > 0:
			PREVIEW_TYPE = 'MATERIAL'
		else:
			preview_objects = [o for o in objects_mats.keys() if o.name.startswith('texture')]
			if len(preview_objects) > 0:
				PREVIEW_TYPE = 'TEXTURE'
		
		if PREVIEW_TYPE == None:
			return
		
		# TODO: scene setup based on PREVIEW_TYPE
		
		# find the materials attached to the likely preview object
		likely_materials = objects_mats[preview_objects[0]]
		if len(likely_materials) < 1:
			print('no preview materials')
			return
		
		pm = likely_materials[0]
		LuxLog('Rendering material preview: %s' % pm.name)
		
		LM = LuxManager(
			scene.name,
			api_type = 'API',
		)
		LuxManager.SetCurrentScene(scene)
		LuxManager.SetActive(LM)
		
		file_based_preview = False
		
		if file_based_preview:
			# Dump to file in temp dir for debugging
			from ..outputs.file_api import Custom_Context as lxs_writer
			preview_context = lxs_writer(scene.name)
			preview_context.set_filename('luxblend25-preview', LXS=True, LXM=False, LXO=False)
			LM.lux_context = preview_context
		else:
			preview_context = LM.lux_context
			preview_context.logVerbosity('quiet')
		
		try:
			export_materials.ExportedMaterials.clear()
			export_materials.ExportedTextures.clear()
			
			from ..export import preview_scene
			xres, yres = scene.camera.data.luxrender_camera.luxrender_film.resolution()
			xres, yres = int(xres), int(yres)
			
			# Don't render the tiny images
			if xres <= 96:
				raise Exception('Preview image too small (%ix%i)' % (xres,yres))
			
			preview_scene.preview_scene(scene, preview_context, obj=preview_objects[0], mat=pm)
			
			# render !
			preview_context.worldEnd()
			
			if file_based_preview:
				preview_context = preview_context.parse('luxblend25-preview.lxs', True)
				LM.lux_context = preview_context
			
			while not preview_context.statistics('sceneIsReady'):
				time.sleep(0.05)
			
			def is_finished(ctx):
				#future
				#return ctx.getAttribute('renderer', 'state') == ctx.PYLUX.Renderer.State.TERMINATE
				return ctx.statistics('enoughSamples') == 1.0
			
			def interruptible_sleep(sec, increment=0.05):
				sec_elapsed = 0.0
				while not self.test_break() and sec_elapsed<=sec:
					sec_elapsed += increment
					time.sleep(increment)
			
			for i in range(multiprocessing.cpu_count()-2):
				# -2 since 1 thread already created and leave 1 spare
				if is_finished(preview_context):
					break
				preview_context.addThread()
			
			while not is_finished(preview_context):
				if self.test_break():
					raise Exception('Render interrupted')
				
				# progressively update the preview
				time.sleep(0.2) # safety-sleep
				if LUXRENDER_VERSION < '0.8' or preview_context.statistics('samplesPx') > 24:
					interruptible_sleep(1.8) # up to HALTSPP every 2 seconds in sum
					
				LuxLog('Updating preview (%ix%i - %s)' % (xres, yres, preview_context.printableStatistics(False)))
				
				result = self.begin_result(0, 0, xres, yres)
				lay = result.layers[0]
				
				lay.rect, no_z_buffer  = preview_context.blenderCombinedDepthRects()
				
				self.end_result(result)
		except Exception as exc:
			LuxLog('Preview aborted: %s' % exc)
		
		preview_context.exit()
		preview_context.wait()
		
		# cleanup() destroys the pylux Context
		preview_context.cleanup()
		
		LM.reset()
	
	def render_scene(self, scene):
		scene_path = efutil.filesystem_path(scene.render.filepath)
		if os.path.isdir(scene_path):
			self.output_dir = scene_path
		else:
			self.output_dir = os.path.dirname( scene_path )
		
		if self.output_dir[-1] != '/':
			self.output_dir += '/'
		
		if scene.luxrender_engine.export_type == 'INT': # and not scene.luxrender_engine.write_files:
			write_files = scene.luxrender_engine.write_files
			if write_files:
				api_type = 'FILE'
			else:
				api_type = 'API'
				self.output_dir = efutil.temp_directory()
		
		elif scene.luxrender_engine.export_type == 'LFC':
			api_type = 'LUXFIRE_CLIENT'
			write_files = False
		else:
			api_type = 'FILE'
			write_files = True
		
		efutil.export_path = self.output_dir
		#print('(1) export_path is %s' % efutil.export_path)
		os.chdir(self.output_dir)
		
		# Pre-allocate the LuxManager so that we can set up the network servers before export
		LM = LuxManager(
			scene.name,
			api_type = api_type,
		)
		LuxManager.SetActive(LM)
		
		if scene.luxrender_engine.export_type == 'INT':
			# Set up networking before export so that we get better server usage
			if scene.luxrender_networking.use_network_servers:
				LM.lux_context.setNetworkServerUpdateInterval( scene.luxrender_networking.serverinterval )
				for server in scene.luxrender_networking.servers.split(','):
					LM.lux_context.addServer(server.strip())
		
		output_filename = efutil.scene_filename() + '.%s.%05i' % (scene.name, scene.frame_current)
		
		scene_exporter = SceneExporter()
		scene_exporter.properties.directory = self.output_dir
		scene_exporter.properties.filename = output_filename
		scene_exporter.properties.api_type = api_type			# Set export target
		scene_exporter.properties.write_files = write_files		# Use file write decision from above
		scene_exporter.properties.write_all_files = False		# Use UI file write settings
		scene_exporter.set_scene(scene)
		
		export_result = scene_exporter.export()
		
		if 'CANCELLED' in export_result:
			return False
		
		# Look for an output image to load
		if scene.camera.data.luxrender_camera.luxrender_film.write_png:
			self.output_file = efutil.path_relative_to_export(
				'%s/%s.png' % (self.output_dir, output_filename)
			)
		elif scene.camera.data.luxrender_camera.luxrender_film.write_tga:
			self.output_file = efutil.path_relative_to_export(
				'%s/%s.tga' % (self.output_dir, output_filename)
			)
		elif scene.camera.data.luxrender_camera.luxrender_film.write_exr:
			self.output_file = efutil.path_relative_to_export(
				'%s/%s.exr' % (self.output_dir, output_filename)
			)
		
		return True
	
	def render_start(self, scene):
		self.LuxManager = LuxManager.ActiveManager
		
		# TODO: this will be removed when direct framebuffer
		# access is implemented in Blender
		if os.path.exists(self.output_file):
			# reset output image file and
			os.remove(self.output_file)
		
		internal	= (scene.luxrender_engine.export_type in ['INT', 'LFC'])
		write_files	= scene.luxrender_engine.write_files and (scene.luxrender_engine.export_type in ['INT', 'EXT'])
		render		= scene.luxrender_engine.render or (scene.luxrender_engine.export_type in ['LFC'])
		
		# Handle various option combinations using simplified variable names !
		if internal:
			if write_files:
				if render:
					start_rendering = True
					parse = True
					worldEnd = False
				else:
					start_rendering = False
					parse = False
					worldEnd = False
			else:
				# will always render
				start_rendering = True
				parse = False
				worldEnd = True
		else:
			# external always writes files
			if render:
				start_rendering = True
				parse = False
				worldEnd = False
			else:
				start_rendering = False
				parse = False
				worldEnd = False
		
		#print('internal %s' % internal)
		#print('write_files %s' % write_files)
		#print('render %s' % render)
		#print('start_rendering %s' % start_rendering)
		#print('parse %s' % parse)
		#print('worldEnd %s' % worldEnd)
		
		if self.LuxManager.lux_context.API_TYPE == 'FILE':
			fn = self.LuxManager.lux_context.file_names[0]
			
			#print('calling pylux.context.worldEnd() (1)')
			self.LuxManager.lux_context.worldEnd()
			if parse:
				# file_api.parse() creates a real pylux context. we must replace
				# LuxManager's context with that one so that the running renderer
				# can be controlled.
				ctx = self.LuxManager.lux_context.parse(fn, True)
				self.LuxManager.lux_context = ctx
				self.LuxManager.stats_thread.LocalStorage['lux_context'] = ctx
				self.LuxManager.fb_thread.LocalStorage['lux_context'] = ctx
		elif worldEnd:
			#print('calling pylux.context.worldEnd() (2)')
			self.LuxManager.lux_context.worldEnd()
		
		# Begin rendering
		if start_rendering:
			LuxLog('Starting LuxRender')
			if internal:
				
				self.LuxManager.lux_context.logVerbosity(scene.luxrender_engine.log_verbosity)
				
				self.update_stats('', 'LuxRender: Rendering warmup')
				self.LuxManager.start()
				
				self.LuxManager.fb_thread.LocalStorage['integratedimaging'] = scene.camera.data.luxrender_camera.luxrender_film.integratedimaging
				
				if scene.camera.data.luxrender_camera.luxrender_film.integratedimaging:
					# Use the GUI update interval
					self.LuxManager.fb_thread.set_kick_period( scene.camera.data.luxrender_camera.luxrender_film.displayinterval )
				else:
					# Update the image from disk only as often as it is written
					self.LuxManager.fb_thread.set_kick_period( scene.camera.data.luxrender_camera.luxrender_film.writeinterval )
				
				# Start the stats and framebuffer threads and add additional threads to Lux renderer
				self.LuxManager.start_worker_threads(self)
				
				if scene.luxrender_engine.threads_auto:
					try:
						thread_count = multiprocessing.cpu_count()
					except:
						# TODO: when might this fail?
						thread_count = 1
				else:
					thread_count = scene.luxrender_engine.threads
				
				# Run rendering with specified number of threads
				for i in range(thread_count - 1):
					self.LuxManager.lux_context.addThread()
				
				while self.LuxManager.started:
					self.render_update_timer = threading.Timer(1, self.stats_timer)
					self.render_update_timer.start()
					if self.render_update_timer.isAlive(): self.render_update_timer.join()
			else:
				config_updates = {
					'auto_start': render
				}
				
				luxrender_path = efutil.filesystem_path( scene.luxrender_engine.install_path )
				if luxrender_path[-1] != '/':
					luxrender_path += '/'
				
				if os.path.isdir(luxrender_path) and os.path.exists(luxrender_path):
					config_updates['install_path'] = luxrender_path
				
				if sys.platform == 'darwin' and scene.luxrender_engine.binary_name == 'luxrender':
					# Get binary from OSX package
					luxrender_path += 'luxrender.app/Contents/MacOS/luxrender'
				elif sys.platform == 'win32':
					luxrender_path += '%s.exe' % scene.luxrender_engine.binary_name
				else:
					luxrender_path += scene.luxrender_engine.binary_name
				
				if not os.path.exists(luxrender_path):
					LuxLog('LuxRender not found at path: %s' % luxrender_path)
					return False
				
				cmd_args = [luxrender_path, fn]
				
				# set log verbosity
				if scene.luxrender_engine.log_verbosity != 'default':
					cmd_args.append('--' + scene.luxrender_engine.log_verbosity)
				
				if scene.luxrender_engine.binary_name == 'luxrender':
					# Copy the GUI log to the console
					cmd_args.append('--logconsole')
				
				# Set number of threads for external processes
				if not scene.luxrender_engine.threads_auto:
					cmd_args.append('--threads=%i' % scene.luxrender_engine.threads)
				
				if scene.luxrender_networking.use_network_servers:
					for server in scene.luxrender_networking.servers.split(','):
						cmd_args.append('--useserver')
						cmd_args.append(server.strip())
					
					cmd_args.append('--serverinterval')
					cmd_args.append('%i' % scene.luxrender_networking.serverinterval)
					
					config_updates['servers'] = scene.luxrender_networking.servers
					config_updates['serverinterval'] = '%i' % scene.luxrender_networking.serverinterval
				
				config_updates['use_network_servers'] = scene.luxrender_networking.use_network_servers
				
				# Save changed config items and then launch Lux
				
				try:
					for k, v in config_updates.items():
						efutil.write_config_value('luxrender', 'defaults', k, v)
				except Exception as err:
					LuxLog('WARNING: Saving LuxRender config failed, please set your user scripts dir: %s' % err)
				
				LuxLog('Launching: %s' % cmd_args)
				# LuxLog(' in %s' % self.outout_dir)
				luxrender_process = subprocess.Popen(cmd_args, cwd=self.output_dir)
				framebuffer_thread = LuxFilmDisplay({
					'resolution': scene.camera.data.luxrender_camera.luxrender_film.resolution(),
					'RE': self,
				})
				framebuffer_thread.set_kick_period( scene.camera.data.luxrender_camera.luxrender_film.writeinterval ) 
				framebuffer_thread.start()
				while luxrender_process.poll() == None and not self.test_break():
					self.render_update_timer = threading.Timer(1, self.process_wait_timer)
					self.render_update_timer.start()
					if self.render_update_timer.isAlive(): self.render_update_timer.join()
				
				# If we exit the wait loop (user cancelled) and luxconsole is still running, then send SIGINT
				if luxrender_process.poll() == None and scene.luxrender_engine.binary_name != 'luxrender':
					# Use SIGTERM because that's the only one supported on Windows
					luxrender_process.send_signal(subprocess.signal.SIGTERM)
				
				# Stop updating the render result and load the final image
				framebuffer_thread.stop()
				framebuffer_thread.join()
				framebuffer_thread.kick(render_end=True)
	
	def process_wait_timer(self):
		# Nothing to do here
		pass
	
	def stats_timer(self):
		'''
		Update the displayed rendering statistics and detect end of rendering
		
		Returns None
		'''
		
		self.update_stats('', 'LuxRender: Rendering %s' % self.LuxManager.stats_thread.stats_string)
		if self.test_break() or \
			self.LuxManager.lux_context.statistics('filmIsReady') == 1.0 or \
			self.LuxManager.lux_context.statistics('terminated') == 1.0 or \
			self.LuxManager.lux_context.statistics('enoughSamples') == 1.0:
			self.LuxManager.reset()
			self.update_stats('', '')
