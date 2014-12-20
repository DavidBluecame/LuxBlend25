# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Simon Wendsche (BYOB)
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

from ..extensions_framework import declarative_property_group

from .. import LuxRenderAddon


@LuxRenderAddon.addon_register_class
class luxcore_realtimesettings(declarative_property_group):
    """
    Storage class for LuxCore realtime preview settings.
    """

    ef_attach_to = ['Scene']

    controls = [
        'use_finalrender_settings',
        'device_type', 
        'advanced',
        'cpu_renderengine_type',
        'ocl_renderengine_type',
        'sampler_type'
    ]

    visibility = {
                    'device_type': {'use_finalrender_settings': False},
                    'advanced': {'use_finalrender_settings': False},
                    'cpu_renderengine_type': {'advanced': True, 'device_type': 'CPU', 'use_finalrender_settings': False},
                    'ocl_renderengine_type': {'advanced': True, 'device_type': 'OCL', 'use_finalrender_settings': False},
                    'sampler_type': {'advanced': True, 'use_finalrender_settings': False}
    }

    alert = {}

    properties = [
        {
            'type': 'bool',
            'attr': 'use_finalrender_settings',
            'name': 'Use Final Render Settings',
            'description': 'Use the final render settings for the realtime preview',
            'default': False,
            'save_in_preset': True
        },
        {
            'type': 'enum',
            'attr': 'device_type',
            'name': 'Device',
            'description': 'CPU rendering has lower latency, GPU rendering is faster',
            'default': 'CPU',
            'items': [
                ('CPU', 'CPU', 'Use the CPU (lower latency)'),
                ('OCL', 'OpenCL', 'Use the graphics card via OpenCL (higher latency)'),
            ],
            'save_in_preset': True
        },
        {
            'type': 'bool',
            'attr': 'advanced',
            'name': 'Advanced Settings',
            'description': 'Configure advanced settings',
            'default': False,
            'save_in_preset': True
        },
        {
            'type': 'enum',
            'attr': 'cpu_renderengine_type',
            'name': 'Rendering engine',
            'description': 'Rendering engine to use',
            'default': 'PATHCPU',
            'items': [
                ('PATHCPU', 'Path', 'Path tracer'),
                ('BIDIRCPU', 'Bidir', 'Bidirectional path tracer'),
            ],
            'save_in_preset': True
        },
        {
            'type': 'enum',
            'attr': 'ocl_renderengine_type',
            'name': 'Rendering engine',
            'description': 'Rendering engine to use',
            'default': 'PATHOCL',
            'items': [
                ('PATHOCL', 'Path OpenCL', 'Pure OpenCL path tracer'),
            ],
            'save_in_preset': True
        },
        {
            'type': 'enum',
            'attr': 'sampler_type',
            'name': 'Sampler',
            'description': 'Pixel sampling algorithm to use',
            'default': 'METROPOLIS',
            'items': [
                ('METROPOLIS', 'Metropolis', 'Use in complex lighting situations'),
                ('SOBOL', 'Sobol', 'Use in simple lighting situations'),
                ('RANDOM', 'Random', 'Completely random sampler, not recommended')
            ],
            'save_in_preset': True
        },
    ]
