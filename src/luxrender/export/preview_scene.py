# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
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
import bpy

from ..export import ParamSet
from ..export.geometry import GeometryExporter
from ..export.materials import get_material_volume_defs
from ..outputs import LuxManager
from ..outputs.pure_api import LUXRENDER_VERSION

def preview_scene(scene, lux_context, obj=None, mat=None):
	HALTSPP = 256

	# Camera
	lux_context.lookAt(0.0,-3.0,0.5, 0.0,-2.0,0.5, 0.0,0.0,1.0)
	camera_params = ParamSet().add_float('fov', 22.5)
	lux_context.camera('perspective', camera_params)
	
	# Film
	xr, yr = scene.camera.data.luxrender_camera.luxrender_film.resolution(scene)
	
	film_params = ParamSet() \
		.add_integer('xresolution', xr) \
		.add_integer('yresolution', yr) \
		.add_string('filename', 'luxblend25-preview') \
		.add_bool('write_exr_ZBuf', True) \
		.add_bool('write_exr_applyimaging', True) \
		.add_string('write_exr_channels', 'RGBA') \
		.add_bool('write_exr_halftype', False) \
		.add_float('gamma', 1.0) \
		.add_bool('write_png', False) \
		.add_bool('write_tga', False) \
		.add_bool('write_resume_flm', False) \
		.add_integer('displayinterval', 3) \
		.add_integer('haltspp', HALTSPP) \
		.add_string('tonemapkernel', 'linear') \
		.add_integer('reject_warmup', 64)
	
	if LUXRENDER_VERSION >= '0.8':
		film_params \
			.add_bool('write_exr', False) \
			.add_integer('writeinterval', 3600)
	else:
		film_params \
			.add_bool('write_exr', True) \
			.add_integer('writeinterval', 2)
	lux_context.film('fleximage', film_params)
	
	# Pixel Filter
	pixelfilter_params = ParamSet() \
		.add_float('xwidth', 1.5) \
		.add_float('ywidth', 1.5) \
		.add_float('B', 0.333) \
		.add_float('C', 0.333) \
		.add_bool('supersample', True)
	lux_context.pixelFilter('mitchell', pixelfilter_params)
	
	# Sampler
	if False:
		sampler_params = ParamSet() \
			.add_string('pixelsampler', 'hilbert') \
			.add_integer('pixelsamples', 2)
		lux_context.sampler('lowdiscrepancy', sampler_params)
	else:
		lux_context.sampler('metropolis', ParamSet())
	
	# Surface Integrator
	if False:
		surfaceintegrator_params = ParamSet() \
			.add_integer('directsamples', 1) \
			\
			.add_integer('diffusereflectdepth', 1) \
			.add_integer('diffusereflectsamples', 4) \
			.add_integer('diffuserefractdepth', 4) \
			.add_integer('diffuserefractsamples', 1) \
			\
			.add_integer('glossyreflectdepth', 1) \
			.add_integer('glossyreflectsamples', 2) \
			.add_integer('glossyrefractdepth', 4) \
			.add_integer('glossyrefractsamples', 1) \
			\
			.add_integer('specularreflectdepth', 2) \
			.add_integer('specularrefractdepth', 4)
		lux_context.surfaceIntegrator('distributedpath', surfaceintegrator_params)
	else:
		lux_context.surfaceIntegrator('bidirectional', ParamSet())
	
	# Volume Integrator
	lux_context.volumeIntegrator('multi', ParamSet())
	
	lux_context.worldBegin()
	
	# Collect volumes from all scenes *sigh*
	for scn in bpy.data.scenes:
		LuxManager.SetCurrentScene(scn)
		for volume in scn.luxrender_volumes.volumes:
			lux_context.makeNamedVolume( volume.name, *volume.api_output(lux_context) )

#	LuxManager.SetCurrentScene(scene) # here we get wrong scene ( previev instead of active scene )
	scene = bpy.data.scenes[bpy.context.scene.name]  # intermediate fix but looses context sometimes
#	print("--------->", scene)

	# Light
	lux_context.attributeBegin()
	if mat.preview_render_type == 'FLAT':
		lux_context.transform([
			0.5, 0.0, 0.0, 0.0,
			0.0, 0.5, 0.0, 0.0,
			0.0, 0.0, 0.5, 0.0,
			2.5, -2.5, 2.5, 1.0
		])
	else:
		lux_context.transform([
			0.5996068120002747, 0.800294816493988, 2.980232594040899e-08, 0.0,
			-0.6059534549713135, 0.45399996638298035, 0.6532259583473206, 0.0,
			0.5227733850479126, -0.3916787803173065, 0.7571629285812378, 0.0,
			4.076245307922363, -3.0540552139282227, 5.903861999511719, 1.0
		])
	light_bb_params = ParamSet().add_float('temperature', 6500.0)
	lux_context.texture('pL', 'color', 'blackbody', light_bb_params)
	light_params = ParamSet() \
		.add_texture('L', 'pL') \
		.add_float('gain', 1.0) \
		.add_float('importance', 1.0)
	
	if scene.luxrender_world.default_exterior_volume != '':
		lux_context.exterior(scene.luxrender_world.default_exterior_volume)
	lux_context.areaLightSource('area', light_params)

	areax = 1
	areay = 1
	points = [-areax/2.0, areay/2.0, 0.0, areax/2.0, areay/2.0, 0.0, areax/2.0, -areay/2.0, 0.0, -areax/2.0, -areay/2.0, 0.0]
	
	shape_params = ParamSet()
	shape_params.add_integer('ntris', 6)
	shape_params.add_integer('nvertices', 4)
	shape_params.add_integer('indices', [0, 1, 2, 0, 2, 3])
	shape_params.add_point('P', points)
	lux_context.shape('trianglemesh', shape_params)
	lux_context.attributeEnd()
	
	# Add a background color (light)
	if scene.luxrender_world.default_exterior_volume != '':
		lux_context.exterior(scene.luxrender_world.default_exterior_volume)
	lux_context.lightSource('infinite', ParamSet().add_float('gain', 0.1).add_float('importance', 0.1))
	
	# back drop
	if mat.preview_render_type == 'FLAT':
		lux_context.attributeBegin()
		lux_context.transform([
			5.0, 0.0, 0.0, 0.0,
			0.0, 5.0, 0.0, 0.0,
			0.0, 0.0, 5.0, 0.0,
			0.0, 10.0, 0.0, 1.0
		])
		lux_context.scale(4,1,1)
		lux_context.rotate(90, 1,0,0)
		checks_pattern_params = ParamSet() \
			.add_integer('dimension', 2) \
			.add_string('mapping', 'uv') \
			.add_float('uscale', 36.8) \
			.add_float('vscale', 36.0*4)
		lux_context.texture('checks::pattern', 'float', 'checkerboard', checks_pattern_params)
		checks_params = ParamSet() \
			.add_texture('amount', 'checks::pattern') \
			.add_color('tex1', [0.9, 0.9, 0.9]) \
			.add_color('tex2', [0.0, 0.0, 0.0])
		lux_context.texture('checks', 'color', 'mix', checks_params)
		mat_params = ParamSet().add_texture('Kd', 'checks')
		lux_context.material('matte', mat_params)
		bd_shape_params = ParamSet() \
			.add_integer('ntris', 6) \
			.add_integer('nvertices', 4) \
			.add_integer('indices', [0,1,2,0,2,3]) \
			.add_point('P', [
				 1.0,  1.0, 0.0,
				-1.0,  1.0, 0.0,
				-1.0, -1.0, 0.0,
				 1.0, -1.0, 0.0,
			]) \
			.add_normal('N', [
				0.0,  0.0, 1.0,
				0.0,  0.0, 1.0,
				0.0,  0.0, 1.0,
				0.0,  0.0, 1.0,
			]) \
			.add_float('uv', [
				0.333334, 0.000000,
				0.333334, 0.333334,
				0.000000, 0.333334,
				0.000000, 0.000000,
			])
		lux_context.shape('loopsubdiv', bd_shape_params)
	else:
		lux_context.attributeBegin()
		lux_context.transform([
			5.0, 0.0, 0.0, 0.0,
			0.0, 5.0, 0.0, 0.0,
			0.0, 0.0, 5.0, 0.0,
			0.0, 0.0, 0.0, 1.0
		])
		lux_context.scale(4,1,1)
		checks_pattern_params = ParamSet() \
			.add_integer('dimension', 2) \
			.add_string('mapping', 'uv') \
			.add_float('uscale', 36.8) \
			.add_float('vscale', 36.0*4) #.add_string('aamode', 'supersample') \
		lux_context.texture('checks::pattern', 'float', 'checkerboard', checks_pattern_params)
		checks_params = ParamSet() \
			.add_texture('amount', 'checks::pattern') \
			.add_color('tex1', [0.9, 0.9, 0.9]) \
			.add_color('tex2', [0.0, 0.0, 0.0])
		lux_context.texture('checks', 'color', 'mix', checks_params)
		mat_params = ParamSet().add_texture('Kd', 'checks')
		lux_context.material('matte', mat_params)
		bd_shape_params = ParamSet() \
			.add_integer('nlevels', 3) \
			.add_bool('dmnormalsmooth', True) \
			.add_bool('dmsharpboundary', False) \
			.add_integer('ntris', 18) \
			.add_integer('nvertices', 8) \
			.add_integer('indices', [0,1,2,0,2,3,1,0,4,1,4,5,5,4,6,5,6,7]) \
			.add_point('P', [
				 1.0,  1.0, 0.0,
				-1.0,  1.0, 0.0,
				-1.0, -1.0, 0.0,
				 1.0, -1.0, 0.0,
				 1.0,  3.0, 0.0,
				-1.0,  3.0, 0.0,
				 1.0,  3.0, 2.0,
				-1.0,  3.0, 2.0,
			]) \
			.add_normal('N', [
				0.0,  0.000000, 1.000000,
				0.0,  0.000000, 1.000000,
				0.0,  0.000000, 1.000000,
				0.0,  0.000000, 1.000000,
				0.0, -0.707083, 0.707083,
				0.0, -0.707083, 0.707083,
				0.0, -1.000000, 0.000000,
				0.0, -1.000000, 0.000000,
			]) \
			.add_float('uv', [
				0.333334, 0.000000,
				0.333334, 0.333334,
				0.000000, 0.333334,
				0.000000, 0.000000,
				0.666667, 0.000000,
				0.666667, 0.333333,
				1.000000, 0.000000,
				1.000000, 0.333333,
			])
		lux_context.shape('loopsubdiv', bd_shape_params)
	
	if scene.luxrender_world.default_interior_volume != '':
		lux_context.interior(scene.luxrender_world.default_interior_volume)
	if scene.luxrender_world.default_exterior_volume != '':
		lux_context.exterior(scene.luxrender_world.default_exterior_volume)
	
	lux_context.attributeEnd()
	
	if obj is not None and mat is not None:
		# preview object
		lux_context.attributeBegin()
		pv_transform = [
			0.5, 0.0, 0.0, 0.0,
			0.0, 0.5, 0.0, 0.0,
			0.0, 0.0, 0.5, 0.0,
			0.0, 0.0, 0.5, 1.0
		]
		pv_export_shape = True
		
		if mat.preview_render_type == 'FLAT':
			lux_context.scale(1, 1, 8)
			lux_context.rotate(90, 1,0,0)
			pv_transform = [
				0.1, 0.0, 0.0, 0.0,
				0.0, 0.1, 0.0, 0.0,
				0.0, 0.0, 0.2, 0.0,
				0.0, 0.06, -1, 1.0
			]
		if mat.preview_render_type == 'SPHERE':
			pv_transform = [
				0.1, 0.0, 0.0, 0.0,
				0.0, 0.1, 0.0, 0.0,
				0.0, 0.0, 0.1, 0.0,
				0.0, 0.0, 0.5, 1.0
			]
		if mat.preview_render_type == 'CUBE':
			lux_context.scale(0.8, 0.8, 0.8)
			lux_context.rotate(-35, 0,0,1)
		if mat.preview_render_type == 'MONKEY':
			pv_transform = [
				1.0573405027389526, 0.6340668201446533, 0.0, 0.0,
				-0.36082395911216736, 0.601693332195282, 1.013795018196106, 0.0,
				0.5213892459869385, -0.8694445490837097, 0.7015902996063232, 0.0,
				0.0, 0.0, 0.5, 1.0
			]
		if mat.preview_render_type == 'HAIR':
			pv_export_shape = False
		if mat.preview_render_type == 'SPHERE_A':
			pv_export_shape = False
		
		lux_context.concatTransform(pv_transform)
		
		int_v, ext_v = get_material_volume_defs(mat)
		if int_v != '' or ext_v != '':
			if int_v != '': lux_context.interior(int_v)
			if ext_v != '': lux_context.exterior(ext_v)
		
		if int_v == '' and scene.luxrender_world.default_interior_volume != '':
			lux_context.interior(scene.luxrender_world.default_interior_volume)
		if ext_v == '' and scene.luxrender_world.default_exterior_volume != '':
			lux_context.exterior(scene.luxrender_world.default_exterior_volume)
		
		object_is_emitter = hasattr(mat, 'luxrender_emission') and mat.luxrender_emission.use_emission
		if object_is_emitter:
			# lux_context.lightGroup(mat.luxrender_emission.lightgroup, [])
			lux_context.areaLightSource( *mat.luxrender_emission.api_output(obj) )
		
		if pv_export_shape:
			GE = GeometryExporter(lux_context, scene)
			GE.is_preview = True
			GE.geometry_scene = scene
			for mesh_mat, mesh_name, mesh_type, mesh_params in GE.buildNativeMesh(obj):
				mat.luxrender_material.export(scene, lux_context, mat, mode='direct')
				lux_context.shape(mesh_type, mesh_params)
		else:
			lux_context.shape('sphere', ParamSet().add_float('radius', 1.0))
		lux_context.attributeEnd()
		
	# Default 'Camera' Exterior, just before WorldEnd
	if scene.luxrender_world.default_exterior_volume != '':
		lux_context.exterior(scene.luxrender_world.default_exterior_volume)
	
	return int(xr), int(yr)
	