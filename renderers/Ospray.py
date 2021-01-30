# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2021 Howetuft <howetuft@gmail.com>                      *
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

"""OSPRay studio renderer plugin for FreeCAD Render workbench."""

# NOTE: no SDL documentation seems to exist for ospray_studio, so below
# functions have been elaborated by reverse engineering.
# SDL format is JSON
# Suggested documentation links:
# https://github.com/ospray/ospray_studio


import json
import os
import shlex
from subprocess import Popen
from tempfile import mkstemp
from math import degrees, pi

import FreeCAD as App




# ===========================================================================
#                             Write functions
# ===========================================================================


def write_object(name, mesh, material):
    """Compute a string in renderer SDL to represent a FreeCAD object."""

    # Write the mesh as an OBJ tempfile
    # Known bug: mesh.Placement must be null, otherwise computation is wrong
    f_handle, objfile = mkstemp(suffix=".obj", prefix="_")
    os.close(f_handle)
    tmpmesh = mesh.copy()
    tmpmesh.write(objfile)

    # Fix missing object name in OBJ file (mandatory)
    # We want to insert a 'o ...' statement before the first 'f ...'
    with open(objfile, "r") as f:
        buffer = f.readlines()

    i = next(i for i, l in enumerate(buffer) if l.startswith("f "))
    buffer.insert(i, "o %s\n" % name)

    with open(objfile, "w") as f:
        f.write("".join(buffer))

    snippet_obj = """
      {{
        "name": "{n}",
        "type": 20,
        "filename": "{f}"
      }},"""

    return snippet_obj.format(n=name, f=objfile.encode("unicode_escape").decode("utf-8"))


def write_camera(name, pos, updir, target, fov):
    """Compute a string in renderer SDL to represent a camera."""
    # OSP camera's default orientation is target=(0, 0, -1), up=(0, 1, 0)

    snippet = """
  "camera": {{
    "name": "{n}",
    "centerTranslation": {{
      "affine": [{p.x}, {p.y}, {p.z}],
      "linear": {{"x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0], "z": [0.0, 0.0, 1.0]}}
    }},
    "translation": {{
      "affine": [0.0, 0.0, 0.0],
      "linear": {{"x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0], "z": [0.0, 0.0, 1.0]}}
    }},
    "rotation": {{"i": {r[0]}, "j": {r[1]}, "k": {r[2]}, "r": {r[3]}}}
  }},"""
    base = -pos.Base
    rotmat = pos.Rotation.toMatrix()
    rotmat.transpose()  # We have to transpose, as OSP is right-handed
    rotation = App.Rotation(rotmat).Q
    return snippet.format(n=name,
                          p=base,
                          r=rotation)


def write_pointlight(name, pos, color, power):
    """Compute a string in renderer SDL to represent a point light."""
    # Tip: in studio, to visualize where the light is, increase the radius
    snippet = """
      {{
        "name": "lights",
        "subType": "lights",
        "type": 16,
        "children": [
          {{
            "name": "{n}",
            "type": 15,
            "subType": "sphere",
            "children": [
              {{
                "name": "visible",
                "description": "whether the light can be seen directly",
                "sgOnly": false,
                "subType": "bool",
                "type": 1,
                "value": true
              }},
              {{
                "name": "intensity",
                "description": "intensity of the light (a factor)",
                "sgOnly": false,
                "subType": "float",
                "type": 1,
                "value": {s}
              }},
              {{
                "name": "color",
                "description": "color of the light",
                "sgOnly": false,
                "subType": "rgb",
                "type": 1,
                "value": [{c[0]}, {c[1]}, {c[2]}]
              }},
              {{
                "name": "position",
                "description": "position of the light",
                "sgOnly": false,
                "subType": "vec3f",
                "type": 1,
                "value": [{p[0]}, {p[1]}, {p[2]}]
              }}
            ]
          }}
        ]
      }},"""

    return snippet.format(n=name,
                          c=color,
                          p=pos,
                          s=power)


def write_arealight(name, pos, size_u, size_v, color, power, transparent):
    """Compute a string in renderer SDL to represent an area light."""

    return ""
    # # Transparent area light
    # rot = pos.Rotation
    # axis1 = rot.multVec(App.Vector(1.0, 0.0, 0.0))
    # axis2 = rot.multVec(App.Vector(0.0, 1.0, 0.0))
    # direction = axis1.cross(axis2)
    # snippet1 = """
    # <!-- Generated by FreeCAD - Area light '{n}' (transparent) -->
    # <shader name="{n}_shader">
        # <emission name="{n}_emit"
                  # color="{c[0]} {c[1]} {c[2]}"
                  # strength="{s}"/>
        # <connect from="{n}_emit emission"
                 # to="output surface"/>
    # </shader>
    # <state shader="{n}_shader">
        # <light type="area"
               # co="{p.x} {p.y} {p.z}"
               # strength="1 1 1"
               # axisu="{u.x} {u.y} {u.z}"
               # axisv="{v.x} {v.y} {v.z}"
               # sizeu="{a}"
               # sizev="{b}"
               # size="1"
               # dir="{d.x} {d.y} {d.z}"
               # use_mis = "true"
        # />
    # </state>\n"""

    # # Opaque area light (--> mesh light)
    # points = [(-size_u / 2, -size_v / 2, 0),
              # (+size_u / 2, -size_v / 2, 0),
              # (+size_u / 2, +size_v / 2, 0),
              # (-size_u / 2, +size_v / 2, 0)]
    # points = [pos.multVec(App.Vector(*p)) for p in points]
    # points = ["{0.x} {0.y} {0.z}".format(p) for p in points]
    # points = "  ".join(points)

    # snippet2 = """
    # <!-- Generated by FreeCAD - Area light '{n}' (opaque) -->
    # <shader name="{n}_shader" use_mis="true">
        # <emission name="{n}_emit"
                  # color="{c[0]} {c[1]} {c[2]}"
                  # strength="{s}"/>
        # <connect from="{n}_emit emission"
                 # to="output surface"/>
    # </shader>
    # <state shader="{n}_shader">
        # <mesh P="{P}"
              # nverts="4"
              # verts="0 1 2 3"
              # use_mis="true"
              # />
    # </state>\n"""

    # snippet = snippet1 if transparent else snippet2
    # strength = power if transparent else power / (size_u * size_v)

    # return snippet.format(n=name,
                          # c=color,
                          # p=pos.Base,
                          # s=strength * 100,
                          # u=axis1,
                          # v=axis2,
                          # a=size_u,
                          # b=size_v,
                          # d=direction,
                          # P=points)


def write_sunskylight(name, direction, distance, turbidity, albedo):
    """Compute a string in renderer SDL to represent a sunsky light."""
    # We model sun_sky with a sun light and a sky texture for world

    # # For sky texture, direction must be normalized
    # assert direction.Length
    # _dir = App.Vector(direction)
    # _dir.normalize()
    # theta = acos(_dir.z / sqrt(_dir.x**2 + _dir.y**2 + _dir.z**2))
    # sun = sunlight(theta, turbidity)
    # rgb = sun.xyz.to_srgb_with_fixed_luminance(1.)

    # strength = sun.irradiance / 100
    # # Real physical angle should be about 0.5°, but it results into very sharp
    # # shadows...
    # angle = radians(0.5)

    # snippet = """
    # <!-- Generated by FreeCAD - Sun_sky light '{n}' -->
    # <background name="sky_bg">
          # <background name="sky_bg" />
          # <sky_texture name="sky_tex"
                       # type="hosek_wilkie"
                       # turbidity="{t}"
                       # sun_direction="{d.x}, {d.y}, {d.z}"
                       # ground_albedo="{g}" />
          # <connect from="sky_tex color" to="sky_bg color" />
          # <connect from="sky_bg background" to="output surface" />
    # </background>
    # <shader name="{n}_shader">
        # <emission name="{n}_emit"
                  # color="{c[0]} {c[1]} {c[2]}"
                  # strength="{s}"/>
        # <connect from="{n}_emit emission" to="output surface"/>
    # </shader>
    # <state shader="{n}_shader">
        # <light type="distant"
               # co="1 1 1"
               # strength="1 1 1"
               # dir="{v.x}, {v.y}, {v.z}"
               # angle="{a}"/>
    # </state>\n"""
    # return snippet.format(n=name,
                          # d=_dir,
                          # t=turbidity,
                          # c=rgb,
                          # s=strength,
                          # a=angle,
                          # v=-_dir,
                          # g=albedo
                          # )


def write_imagelight(name, image):
    """Compute a string in renderer SDL to represent an image-based light."""
    # Caveat: Cycles requires the image file to be in the same directory
    # as the input file
    return ""
    # filename = pathlib.Path(image).name
    # snippet = """
    # <!-- Generated by FreeCAD - Image-based light '{n}' -->
    # <background>
          # <background name="{n}_bg" />
          # <environment_texture name= "{n}_tex"
                               # filename = "{f}" />
          # <connect from="{n}_tex color" to="{n}_bg color" />
          # <connect from="{n}_bg background" to="output surface" />
    # </background>\n"""
    # return snippet.format(n=name,
                          # f=filename,)


# ===========================================================================
#                              Material implementation
# ===========================================================================


def _write_material(name, material):
    """Compute a string in the renderer SDL, to represent a material.

    This function should never fail: if the material is not recognized,
    a fallback material is provided.
    """
    try:
        snippet_mat = MATERIALS[material.shadertype](name, material)
    except KeyError:
        msg = ("'{}' - Material '{}' unknown by renderer, using fallback "
               "material\n")
        App.Console.PrintWarning(msg.format(name, material.shadertype))
        snippet_mat = _write_material_fallback(name, material.default_color)
    return snippet_mat


def _write_material_passthrough(name, material):
    """Compute a string in the renderer SDL for a passthrough material."""
    assert material.passthrough.renderer == "Cycles"
    snippet = indent(material.passthrough.string, "    ")
    return snippet.format(n=name, c=material.default_color)


def _write_material_glass(name, material):
    """Compute a string in the renderer SDL for a glass material."""
    snippet = """
    <!-- Generated by FreeCAD - Object '{n}' -->
    <shader name="{n}">
        <glass_bsdf name="{n}_bsdf" IOR="{i}" color="{c.r}, {c.g}, {c.b}"/>
        <connect from="{n}_bsdf bsdf" to="output surface"/>
    </shader>"""

    return snippet.format(n=name,
                          c=material.glass.color,
                          i=material.glass.ior)


def _write_material_disney(name, material):
    """Compute a string in the renderer SDL for a Disney material."""
    snippet = """
    <!-- Generated by FreeCAD - Object '{0}' -->
    <shader name="{0}">
        <principled_bsdf name="{0}_bsdf"
                         base_color = "{1.r} {1.g} {1.b}"
                         subsurface = "{2}"
                         metallic = "{3}"
                         specular = "{4}"
                         specular_tint = "{5}"
                         roughness = "{6}"
                         anisotropic = "{7}"
                         sheen = "{8}"
                         sheen_tint = "{9}"
                         clearcoat = "{10}"
                         clearcoat_roughness = "{11}" />
        <connect from="{0}_bsdf bsdf" to="output surface"/>
    </shader>"""
    return snippet.format(name,
                          material.disney.basecolor,
                          material.disney.subsurface,
                          material.disney.metallic,
                          material.disney.specular,
                          material.disney.speculartint,
                          material.disney.roughness,
                          material.disney.anisotropic,
                          material.disney.sheen,
                          material.disney.sheentint,
                          material.disney.clearcoat,
                          1 - float(material.disney.clearcoatgloss))


def _write_material_diffuse(name, material):
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet = """
    <!-- Generated by FreeCAD - Object '{n}' -->
    <shader name="{n}">
        <diffuse_bsdf name="{n}_bsdf" color="{c.r}, {c.g}, {c.b}"/>
        <connect from="{n}_bsdf bsdf" to="output surface"/>
    </shader>"""
    return snippet.format(n=name,
                          c=material.diffuse.color)


def _write_material_mixed(name, material):
    """Compute a string in the renderer SDL for a Mixed material."""
    snippet = """
    <!-- Generated by FreeCAD - Object '{n}' -->
    <shader name="{n}">
        <glass_bsdf name="{n}_glass_bsdf"
                    IOR="{i}" color="{c.r}, {c.g}, {c.b}"/>
        <diffuse_bsdf name="{n}_diffuse_bsdf" color="{k.r}, {k.g}, {k.b}"/>
        <mix_closure name="{n}_closure" fac="{r}" />
        <connect from="{n}_diffuse_bsdf bsdf" to="{n}_closure closure1"/>
        <connect from="{n}_glass_bsdf bsdf" to="{n}_closure closure2"/>
        <connect from="{n}_closure closure" to="output surface"/>
    </shader>"""
    return snippet.format(n=name,
                          c=material.mixed.glass.color,
                          i=material.mixed.glass.ior,
                          k=material.mixed.diffuse.color,
                          r=material.mixed.transparency)


def _write_material_fallback(name, material):
    """Compute a string in the renderer SDL for a fallback material.

    Fallback material is a simple Diffuse material.
    """
    try:
        red = float(material.default_color.r)
        grn = float(material.default_color.g)
        blu = float(material.default_color.b)
        assert (0 <= red <= 1) and (0 <= grn <= 1) and (0 <= blu <= 1)
    except (AttributeError, ValueError, TypeError, AssertionError):
        red, grn, blu = 1, 1, 1
    snippet = """
    <!-- Generated by FreeCAD - Object '{n}' - FALLBACK -->
    <shader name="{n}">
        <diffuse_bsdf name="{n}_bsdf" color="{r}, {g}, {b}"/>
        <connect from="{n}_bsdf bsdf" to="output surface"/>
    </shader>"""
    return snippet.format(n=name,
                          r=red,
                          g=grn,
                          b=blu)


MATERIALS = {
        "Passthrough": _write_material_passthrough,
        "Glass": _write_material_glass,
        "Disney": _write_material_disney,
        "Diffuse": _write_material_diffuse,
        "Mixed": _write_material_mixed}


# ===========================================================================
#                              Render function
# ===========================================================================


def render(project, prefix, external, output, width, height):
    """Run renderer.

    Args:
        project -- The project to render
        prefix -- A prefix string for call (will be inserted before path to
            renderer)
        external -- A boolean indicating whether to call UI (true) or console
            (false) version of renderder
        width -- Rendered image width, in pixels
        height -- Rendered image height, in pixels

    Returns:
        A path to output image file
    """
    # TODO Pythonicize...

    # Clean input file (move cameras to header)
    cameras = ['\n']
    result = list()
    with open(project.PageResult, "r") as f:
        def count_delimiters(line):
            return line.count('{') - line.count('}')
        for line in f:
            if '"camera"' in line:
                cameras += line
                nbr = count_delimiters(line)
                for line in f:
                    nbr += count_delimiters(line)
                    cameras += line
                    if not nbr:
                        break
            else:
               result += line
        result[2:2] = cameras
        result = ''.join(result)

    # Merge light groups
    json_load = json.loads(result)
    world_children = json_load["world"]["children"]
    world_children.sort(key=lambda x: x["type"]==16)  # Light groups last

    lights = list()
    def remaining_lightgroups():
        try:
            child = world_children[-1]
        except IndexError:
            return False
        return child["type"]==16
    while remaining_lightgroups():
        light = world_children.pop()
        lights += (light["children"])
    lightgroup = {"description": "Lights",
                  "name": "lights",
                  "subType": "lights",
                  "type": 16,
                  "children": lights}
    world_children.insert(0, lightgroup)


    # Write resulting output to file
    f_handle, f_path = mkstemp(
        prefix=project.Name,
        suffix=os.path.splitext(project.Template)[-1])
    os.close(f_handle)
    with open(f_path, "w") as f:
        f.write(json.dumps(json_load, indent=2))
    project.PageResult = f_path
    os.remove(f_path)
    App.ActiveDocument.recompute()

    # Build command and launch
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    prefix = params.GetString("Prefix", "")
    if prefix:
        prefix += " "
    rpath = params.GetString("OspPath", "")
    args = params.GetString("OspParameters", "")
    # args += " --output " + output
    # if not external:
        # args += " --background"
    if not rpath:
        App.Console.PrintError("Unable to locate renderer executable. "
                               "Please set the correct path in "
                               "Edit -> Preferences -> Render\n")
        return ""
    # args += " --width " + str(width)
    # args += " --height " + str(height)
    cmd = prefix + rpath + " " + args + " " + project.PageResult
    App.Console.PrintMessage(cmd+'\n')

    try:
        Popen(shlex.split(cmd))
    except OSError as err:
        msg = "OspStudio call failed: '" + err.strerror + "'\n"
        App.Console.PrintError(msg)

    return None
