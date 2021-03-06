# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# This preset file was generated by LuxBlend25 and modified by Jason Clarke
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
bpy.context.scene.luxrender_rendermode.rendermode = 'exphotonmap'
bpy.context.scene.luxrender_rendermode.renderer = 'sampler'
bpy.context.scene.luxrender_sampler.sampler = 'lowdiscrepancy'
bpy.context.scene.luxrender_sampler.pixelsampler = 'lowdiscrepancy'
bpy.context.scene.luxrender_sampler.pixelsamples = 16
bpy.context.scene.luxrender_integrator.surfaceintegrator = 'exphotonmap'
bpy.context.scene.luxrender_integrator.advanced = False
bpy.context.scene.luxrender_integrator.lightstrategy = 'auto'
bpy.context.scene.luxrender_integrator.maxeyedepth = 16
bpy.context.scene.luxrender_integrator.maxphotondepth = 16
bpy.context.scene.luxrender_integrator.directphotons = 1000000
bpy.context.scene.luxrender_integrator.causticphotons = 10000
bpy.context.scene.luxrender_integrator.indirectphotons = 200000
bpy.context.scene.luxrender_integrator.radiancephotons = 200000
bpy.context.scene.luxrender_integrator.nphotonsused = 50
bpy.context.scene.luxrender_integrator.maxphotondist = 0.10000000149011612
bpy.context.scene.luxrender_integrator.finalgather = True
bpy.context.scene.luxrender_integrator.finalgathersamples = 8
bpy.context.scene.luxrender_integrator.gatherangle = 15.0
bpy.context.scene.luxrender_integrator.renderingmode = 'directlighting'
bpy.context.scene.luxrender_integrator.rrcontinueprob = 0.6499999761581421
bpy.context.scene.luxrender_integrator.rrstrategy = 'efficiency'
bpy.context.scene.luxrender_integrator.includeenvironment = True
bpy.context.scene.luxrender_volumeintegrator.volumeintegrator = 'single'