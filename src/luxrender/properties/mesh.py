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
import bpy

from extensions_framework import declarative_property_group
from extensions_framework.validate import Logic_OR as O, Logic_Operator as LO

from .. import LuxRenderAddon
from ..export import ParamSet
from ..properties.material import texture_append_visibility
from ..properties.texture import FloatTextureParameter, ColorTextureParameter
from ..util import dict_merge

class MeshFloatTextureParameter(FloatTextureParameter):
	def texture_slot_set_attr(self):
		# Looks in a different location than other FloatTextureParameters
		return lambda s,c: c.luxrender_mesh

TF_displacementmap = MeshFloatTextureParameter(
	'dm',
	'Displacement Map',
	real_attr='displacementmap',
	add_float_value=False
)

class MeshColorTextureParameter(ColorTextureParameter):
	def texture_slot_set_attr(self):
		# Looks in a different location than other FloatTextureParameters
		return lambda s,c: c.luxrender_mesh

TC_artexture = MeshColorTextureParameter(
	'projmap',
	'Projector Texture Map',
	real_attr='projectionmap',
	texture_only=True
)

@LuxRenderAddon.addon_register_class
class luxrender_mesh(declarative_property_group):
	'''
	Storage class for LuxRender Camera settings.
	'''
	
	ef_attach_to = ['Mesh', 'SurfaceCurve', 'TextCurve', 'Curve']
	
	controls = [
		'mesh_type',
		'instancing_mode',
		'portal',
		'generatetangents',
		'type',
#		'projection',
	] + \
		TC_artexture.controls + \
	[
		'subdiv',
		'sublevels',
		'mdsublevels',
		'nsmooth',
		['sharpbound', 'splitnormal'],
	] + \
		TF_displacementmap.controls + \
	[
		['dmscale', 'dmoffset']
	]
	
	visibility = dict_merge({
#		'ccam':		{'projection': True },
#		'ucam': 	{'projection': True , 'ccam': False },
		'nsmooth':	{ 'subdiv': 'loop' },
		'sharpbound':	{ 'subdiv': 'loop' },
		'splitnormal':	{ 'subdiv': 'loop' },
		'sublevels':	{ 'subdiv': 'loop' },
		'mdsublevels':  { 'subdiv': 'microdisplacement' },
		'dmscale':		{ 'subdiv': LO({'!=': 'None'}), 'dm_floattexturename': LO({'!=': ''}) },
		'dmoffset':		{ 'subdiv': LO({'!=': 'None'}), 'dm_floattexturename': LO({'!=': ''}) },
	}, TF_displacementmap.visibility, TC_artexture.visibility )
	
	visibility = texture_append_visibility(visibility, TF_displacementmap, { 'subdiv': LO({'!=': 'None'}) })
	visibility = texture_append_visibility(visibility, TC_artexture, { })
	
	properties = [
		{
			'type': 'enum',
			'attr': 'mesh_type',
			'name': 'Export as',
			'items': [
				('global', 'Use default setting', 'global'),
				('native', 'LuxRender mesh', 'native'),
				('binary_ply', 'Binary PLY', 'binary_ply')
			],
			'default': 'global'
		},
		{
			'type': 'enum',
			'attr': 'instancing_mode',
			'name': 'Instancing',
			'items': [
				('auto', 'Automatic', 'Let the exporter code decide'),
				('always', 'Always', 'Always export this mesh as instances'),
				('never', 'Never', 'Never export this mesh as instances')
			],
			'default': 'auto'
		},
		{
			'type': 'bool',
			'attr': 'portal',
			'name': 'Exit Portal',
			'description': 'Use this mesh as an exit portal',
			'default': False,
		},
		{
			'type': 'bool',
			'attr': 'generatetangents',
			'name': 'Generate Tangents',
			'description': 'Generate tanget space for this mesh. Enable when using a bake-generated normal map',
			'default': False,
		},
		{
			'type': 'enum',
			'attr': 'subdiv',
			'name': 'Subdivision Scheme',
			'default': 'None',
			'items': [
				('None', 'None', 'None'),
				('loop', 'Loop', 'loop'),
				('microdisplacement', 'Microdisplacement', 'microdisplacement')
			]
		},
		{
			'type': 'bool',
			'attr': 'nsmooth',
			'name': 'Normal smoothing',
			'description': 'Re-smooth normals after subdividing',
			'default': True,
		},
		{
			'type': 'bool',
			'attr': 'sharpbound',
			'name': 'Sharpen bounds',
			'default': False,
		},
		{
			'type': 'bool',
			'attr': 'splitnormal',
			'name': 'Keep split edges',
			'default': False,
			'description': 'Preserves effects of edge-split modifier with smooth-shaded meshes. WARNING: This will cause solid-shaded meshes to rip open!'},
		{
			'type': 'int',
			'attr': 'sublevels',
			'name': 'Subdivision Levels',
			'default': 2,
			'min': 0,
			'soft_min': 0,
			'max': 6,
			'soft_max': 6
		},
		{
			'type': 'int',
			'attr': 'mdsublevels',
			'name': 'Microsubdivision Levels',
			'default': 50,
			'min': 0,
			'soft_min': 0,
			'max': 1000,
			'soft_max': 1000
		},
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Type',
			'default': 'native',
			'items': [
				('native', 'Native', 'native'),
				('support', 'Support', 'support'),
				('environment', 'Environment', 'environment')
			]
		},
#		{
#			'type': 'bool',
#			'attr': 'projection',
#			'name': 'Use projector texture',
#			'description': 'Select the projector texture type for the object',
#			'default': False,
#		},
		{
			'type': 'bool',
			'attr': 'ccam',
			'name': 'Projection point at current Camera',
			'description': 'Select the position of current camera as the projection point for texture',
			'default': False,
		},
		{
			'type': 'float_vector',
			'attr': 'ucam',
			'name': 'Define Projection point',
			'description': 'Define the projection point for texture',
			'default': (0.0, 0.0, 0.0),
			'save_in_preset': True,
		},
	] + \
		TF_displacementmap.properties + \
	[
		{
			'type': 'float',
			'attr': 'dmscale',
			'name': 'Scale',
			'description': 'Displacement Map Scale',
			'default': 1.0,
			'precision': 6,
			'sub_type': 'DISTANCE',
			'unit': 'LENGTH'
		},
		{
			'type': 'float',
			'attr': 'dmoffset',
			'name': 'Offset',
			'description': 'Displacement Map Offset',
			'default': 0.0,
			'precision': 6,
			'sub_type': 'DISTANCE',
			'unit': 'LENGTH'
		},
	] + \
		TC_artexture.properties

	def get_shape_IsSpecial(self):
		return self.type != 'native'
	
	def get_paramset(self, scene):
		params = ParamSet()
		
		#Export generatetangents
		params.add_bool('generatetangents', self.generatetangents)
		
		# check if subdivision is used
		if self.subdiv != 'None':
			params.add_string('subdivscheme', self.subdiv)
			if self.subdiv == 'loop':
				params.add_integer('nsubdivlevels', self.sublevels)
			elif self.subdiv == 'microdisplacement':
				params.add_integer('nsubdivlevels', self.mdsublevels)
			params.add_bool('dmnormalsmooth', self.nsmooth)
			params.add_bool('dmsharpboundary', self.sharpbound)
			params.add_bool('dmnormalsplit', self.splitnormal)
			
		
		export_dm = TF_displacementmap.get_paramset(self)
		
		if self.dm_floattexturename != '' and len(export_dm) > 0:
			params.add_string('displacementmap', self.dm_floattexturename)
			params.add_float('dmscale', self.dmscale)
			params.add_float('dmoffset', self.dmoffset)

		if self.get_shape_IsSpecial():
			params.add_string('type', self.type)

		export_proj = TC_artexture.get_paramset(self)
		if self.projmap_colortexturename != '' and len(export_proj) > 0:
			params.add_bool('projection', True)
#			cam_pos =  scene.world.texture_slots[self.projmap_colortexturename].texture.luxrender_texture.luxrender_tex_mapping.cam
			cam_pos =  bpy.context.blend_data.textures[self.projmap_colortexturename].luxrender_texture.luxrender_tex_mapping.cam
			params.add_point('cam', ( cam_pos[0], cam_pos[1], cam_pos[2] ) )
#			if self.ccam:
#				cam_pos =  scene.camera.data.luxrender_camera.lookAt(scene.camera)
#				params.add_point('cam', ( cam_pos[0], cam_pos[1], cam_pos[2] ) )
#			else:
#				params.add_point('cam', self.ucam)
		
		return params
