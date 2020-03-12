# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

"""Appleseed renderer for FreeCAD"""

# This file can also be used as a template to add more rendering engines.
# You will need to make sure your file is named with a same name (case
# sensitive)
# That you will use everywhere to describe your renderer, ex: Appleseed or
# Povray


# A render engine module must contain the following functions:
#
# write_camera(pos, rot, up, target, name)
#   returns a string containing an openInventor camera string in renderer
#   format
#
# write_object(view, mesh, color, alpha)
#   returns a string containing a RaytracingView object in renderer format
#
# render(project, prefix, external, output, width, height)
#   renders the given project
#   external means if the user wishes to open the render file in an external
#   application/editor or not. If this is not supported by your renderer, you
#   can simply ignore it
#
# Additionally, you might need/want to add:
#   Preference page items, that can be used in your functions below
#   An icon under the name Renderer.svg (where Renderer is the name of your
#   Renderer


# NOTE: The coordinate system in Appleseed uses a different coordinate system.
# Y and Z are switched and Z is inverted

import os
import re
from tempfile import mkstemp
from math import pi

import FreeCAD as App


def write_camera(pos, rot, updir, target, name):
    """Compute a string in the format of Appleseed, that represents a camera"""
    # This is where you create a piece of text in the format of
    # your renderer, that represents the camera.

    snippet = """
        <camera name="camera" model="thinlens_camera">
            <parameter name="film_width" value="0.032" />
            <parameter name="film_height" value="0.032" />
            <parameter name="aspect_ratio" value="1.7" />
            <parameter name="horizontal_fov" value="40" />
            <parameter name="shutter_open_time" value="0" />
            <parameter name="shutter_close_time" value="1" />
            <parameter name="focal_distance" value="1" />
            <parameter name="f_stop" value="8" />
            <transform>
                <look_at origin="{} {} {}"
                         target="{} {} {}"
                         up="{} {} {}" />
            </transform>
        </camera>"""

    return snippet.format(pos.x, pos.z, -pos.y,
                          target.x, target.z, -target.y,
                          updir.x, updir.z, -updir.y)


def write_object(viewobj, mesh, color, alpha):
    """Compute a string in the format of Appleseed, that represents a FreeCAD
    object
    """
    # This is where you write your object/view in the format of your
    # renderer. "obj" is the real 3D object handled by this project, not
    # the project itself. This is your only opportunity
    # to write all the data needed by your object (geometry, materials, etc)
    # so make sure you include everything that is needed

    # Write the mesh as an OBJ tempfile
    f_handle, objfile = mkstemp(suffix=".obj", prefix="_")
    os.close(f_handle)
    tmpmesh = mesh.copy()
    tmpmesh.rotate(-pi/2, 0, 0)
    tmpmesh.write(objfile)

    # Fix missing object name in OBJ file (mandatory in Appleseed)
    # We want to insert a 'o ...' statement before the first 'f ...'
    with open(objfile, "r") as f:
        buffer = f.readlines()

    i = next(i for i, l in enumerate(buffer) if l.startswith("f "))
    buffer.insert(i, "o %s\n" % viewobj.Name)

    with open(objfile, "w") as f:
        f.write("".join(buffer))

    # Format output
    snippet = """
            <!-- Generated by FreeCAD - Object '{n}' -->
            <color name="{n}_color">
                <parameter name="color_space" value="linear_rgb" />
                <parameter name="multiplier" value="1.0" />
                <parameter name="wavelength_range" value="400.0 700.0" />
                <values> {c[0]} {c[1]} {c[2]} </values>
                <alpha> {a} </alpha>
            </color>
            <bsdf name="{n}_bsdf" model="lambertian_brdf">
                <parameter name="reflectance" value="{n}_color" />
            </bsdf>
            <material name="{n}_mat" model="generic_material">
                <parameter name="bsdf" value="{n}_bsdf" />
                <parameter name="bump_amplitude" value="1.0" />
                <parameter name="bump_offset" value="2.0" />
                <parameter name="displacement_method" value="bump" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="shade_alpha_cutouts" value="false" />
            </material>
            <object name="{o}" model="mesh_object">
                <parameter name="filename" value="{f}" />
            </object>
            <object_instance name="{o}.{n}.instance" object="{o}.{n}">
                <assign_material slot="default"
                                 side="front"
                                 material="{n}_mat" />
                <assign_material slot="default"
                                 side="back"
                                 material="{n}_mat" />
            </object_instance>"""

    return snippet.format(n=viewobj.Name,
                          c=color,
                          a=alpha,
                          o=os.path.splitext(os.path.basename(objfile))[0],
                          f=objfile)


def write_pointlight(view, location, color, power):
    """Compute a string in the format of Appleseed, that represents a
    PointLight object
    """
    # This is where you write the renderer-specific code
    # to export the point light in the renderer format

    # TODO
    return ""


def render(project, prefix, external, output, width, height):
    """Run Appleseed

    Params:
    - project:  the project to render
    - prefix:   a prefix string for call (will be inserted before path to
                renderer)
    - external: a boolean indicating whether to call UI (true) or console
                (false) version of renderder
    - width:    rendered image width, in pixels
    - height:   rendered image height, in pixels

    Return:     path to output image file
    """
    # Here you trigger a render by firing the renderer
    # executable and passing it the needed arguments, and
    # the file it needs to render

    # Change image size in template
    with open(project.PageResult, "r") as f:
        template = f.read()
    res = re.findall(r"<parameter name=\"resolution.*?\/>", template)
    if res:
        snippet = '<parameter name="resolution" value="{} {}"/>'
        template = template.replace(res[0], snippet.format(width, height))
        f_handle, f_path = mkstemp(
            prefix=project.Name,
            suffix=os.path.splitext(project.Template)[-1])
        os.close(f_handle)
        with open(f_path, "w") as f:
            f.write(template)
        project.PageResult = f_path
        os.remove(f_path)
        App.ActiveDocument.recompute()

    # Prepare parameters
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    if external:
        rpath = params.GetString("AppleseedStudioPath", "")
        args = ""
    else:
        rpath = params.GetString("AppleseedCliPath", "")
        args = params.GetString("AppleseedParameters", "")
        if args:
            args += " "
        args += "--output " + output
    if not rpath:
        App.Console.PrintError("Unable to locate renderer executable. "
                               "Please set the correct path in "
                               "Edit -> Preferences -> Render")
        return ""
    if args:
        args += " "
    os.system(prefix + rpath + " " + args + project.PageResult)
    return output
