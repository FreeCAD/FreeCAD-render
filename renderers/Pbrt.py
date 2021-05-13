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

"""pbrt-v4 renderer plugin for FreeCAD Render workbench."""

# Some useful links:
# https://github.com/mmp/pbrt-v4
# https://github.com/mmp/pbrt-v4-scenes
# https://pbrt.org/

import json
import os
import shlex
import re
from subprocess import Popen
from tempfile import mkstemp
from math import degrees, asin, sqrt, atan2

import FreeCAD as App

# Transformation matrix from fcd coords to osp coords
TRANSFORM = App.Placement(App.Matrix(1, 0, 0, 0,
                                     0, 0, 1, 0,
                                     0, -1, 0, 0,
                                     0, 0, 0, 1))

TEMPLATE_FILTER = "Pbrt templates (pbrt_*.pbrt)"

# ===========================================================================
#                             Write functions
# ===========================================================================


def write_object(name, mesh, material):
    """Compute a string in renderer SDL to represent a FreeCAD object."""
    snippet = """# Object '{n}'
AttributeBegin
  Shape "trianglemesh"
    "point3 P" [ {p} ]
    "integer indices" [ {i} ]
AttributeEnd
# ~Object '{n}'
"""
    # TODO material = _write_material(name, material)
    pnts = ["{0.x} {0.y} {0.z}".format(p) for p in mesh.Topology[0]]
    inds = ["{} {} {}".format(*i) for i in mesh.Topology[1]]
    pnts = "  ".join(pnts)
    inds = "  ".join(inds)
    return snippet.format(n=name, p=pnts, i=inds)


def write_camera(name, pos, updir, target, fov):
    """Compute a string in renderer SDL to represent a camera."""
    snippet = """# Camera '{n}'
Scale -1 1 1
LookAt {p.x} {p.y} {p.z}
       {t.x} {t.y} {t.z}
       {u.x} {u.y} {u.z}
Camera "perspective" "float fov" {f}
# ~Camera '{n}'
"""  # NB: do not modify enclosing comments
    return snippet.format(n=name, p=pos.Base, t=target, u=updir, f=fov)


def write_pointlight(name, pos, color, power):
    """Compute a string in renderer SDL to represent a point light."""
    color = [c*power for c in color]
    snippet = """# Pointlight '{n}'
AttributeBegin
  LightSource "point"
    "rgb I" [{c[0]} {c[1]} {c[2]}]
    "point3 from" [{o.x} {o.y} {o.z}]
AttributeEnd
# ~Pointlight '{n}'
"""
    return snippet.format(n=name, o=pos, c=color)


def write_arealight(name, pos, size_u, size_v, color, power, transparent):
    """Compute a string in renderer SDL to represent an area light."""
    # TODO
    return ""
    # # Write mtl file (material)
    # mtl = ["# Created by FreeCAD <http://www.freecadweb.org>",
           # "newmtl material",
           # "type luminous",
           # "color {} {} {}".format(*color),
           # "intensity {}".format(power / 100),
           # "transparency {}".format(1.0 if transparent else 0.0)]

    # f_handle, mtlfile = mkstemp(suffix=".mtl", prefix="light_")
    # os.close(f_handle)
    # with open(mtlfile, "w") as f:
        # f.write('\n'.join(mtl))

    # # Write obj file (geometry)
    # osp_pos = TRANSFORM.multiply(pos)
    # verts = [(-size_u, -size_v, 0),
             # (+size_u, -size_v, 0),
             # (+size_u, +size_v, 0),
             # (-size_u, +size_v, 0)]
    # verts = [osp_pos.multVec(App.Vector(*v)) for v in verts]
    # normal = osp_pos.multVec(App.Vector(0, 0, 1))

    # obj = list()
    # obj += ["# Created by FreeCAD <http://www.freecadweb.org>"]
    # obj += ["mtllib {}".format(os.path.basename(mtlfile))]
    # obj += ["v {0.x} {0.y} {0.z}".format(v) for v in verts]
    # obj += ["vn {0.x} {0.y} {0.z}".format(normal)]
    # obj += ["o {}".format(name)]
    # obj += ["usemtl material"]
    # obj += ["f 1//1 2//1 3//1 4//1"]

    # f_handle, objfile = mkstemp(suffix=".obj", prefix="light_")
    # os.close(f_handle)
    # with open(objfile, "w") as f:
        # f.write('\n'.join(obj))

    # # Return SDL
    # snippet = """
      # {{
        # "name": "{n}",
        # "type": "IMPORTER",
        # "filename": "{f}"
      # }},"""

    # filename = objfile.encode("unicode_escape").decode("utf-8")
    # return snippet.format(n=name, f=filename)


def write_sunskylight(name, direction, distance, turbidity, albedo):
    """Compute a string in renderer SDL to represent a sunsky light."""
    # TODO
    return ""
    # # We make angle calculations in ocp's coordinates system
    # # By default, Up is (0,1,0), Right is (1,0,0), and:
    # #  - North (0°) is z (0, 0, 1)
    # #  - East (90°) is x (1, 0, 0)
    # #  - South (180°) is -z (0, 0, -1)
    # #  - West (270°) is -x (-1, 0, 0)
    # # We'll compute elevation and azimuth accordingly...

    # _dir = TRANSFORM.multVec(App.Vector(direction))
    # elevation = asin(_dir.y / sqrt(_dir.x**2 + _dir.y**2 + _dir.z**2))
    # azimuth = atan2(_dir.x, _dir.z)
    # snippet = """
      # {{
        # "description": "Lights",
        # "name": "lights",
        # "subType": "lights",
        # "type": "LIGHTS",
        # "children": [
          # {{
            # "name": "{n}",
            # "description": "Sunsky light",
            # "type": "LIGHT",
            # "subType": "sunSky",
            # "children": [
              # {{
                # "description": "whether the light can be seen directly",
                # "name": "visible",
                # "sgOnly": false,
                # "subType": "bool",
                # "type": "PARAMETER",
                # "value": true
              # }},
              # {{
                # "description": "intensity of the light (a factor)",
                # "name": "intensity",
                # "sgOnly": false,
                # "subType": "float",
                # "type": "PARAMETER",
                # "value": 1.0
              # }},
              # {{
                # "description": "color of the light",
                # "name": "color",
                # "sgOnly": false,
                # "subType": "rgb",
                # "type": "PARAMETER",
                # "value": [1.0, 1.0, 1.0]
              # }},
              # {{
                # "description": "OSPRay light type",
                # "name": "type",
                # "sgOnly": true,
                # "subType": "string",
                # "type": "PARAMETER",
                # "value": "sunSky"
              # }},
              # {{
                # "description": "Up direction",
                # "name": "up",
                # "sgOnly": false,
                # "subType": "vec3f",
                # "type": "PARAMETER",
                # "value": [0,1,0]
              # }},
              # {{
                # "description": "Right direction",
                # "name": "right",
                # "sgOnly": true,
                # "subType": "vec3f",
                # "type": "PARAMETER",
                # "value": [1,0,0]
              # }},
              # {{
                # "description": "Angle to horizon",
                # "name": "elevation",
                # "sgOnly": true,
                # "subType": "float",
                # "type": "PARAMETER",
                # "value": {e}
              # }},
              # {{
                # "description": "Angle to North",
                # "name": "azimuth",
                # "sgOnly": true,
                # "subType": "float",
                # "type": "PARAMETER",
                # "value": {a}
              # }},
              # {{
                # "description": "Turbidity",
                # "name": "turbidity",
                # "sgOnly": false,
                # "subType": "float",
                # "type": "PARAMETER",
                # "value": {t}
              # }},
              # {{
                # "description": "Ground albedo",
                # "name": "albedo",
                # "sgOnly": false,
                # "subType": "float",
                # "type": "PARAMETER",
                # "value": {g}
              # }}
            # ]
          # }}
        # ]
      # }},"""
    # return snippet.format(n=name,
                          # t=turbidity,
                          # e=degrees(elevation),
                          # a=degrees(azimuth),
                          # g=albedo
                          # )


def write_imagelight(name, image):
    """Compute a string in renderer SDL to represent an image-based light."""
    # TODO
    return ""
    # # At this time (02-15-2021), in current version (0.6.0),
    # # texture import is not serviceable in OspStudio - see here:
    # # https://github.com/ospray/ospray_studio/blob/release-0.6.x/sg/JSONDefs.h#L107
    # # As a workaround, we use a gltf file...

    # gltf_snippet = """
# {{
  # "asset": {{
    # "generator": "FreeCAD Render Workbench",
    # "version": "2.0"
  # }},
  # "scene": 0,
  # "scenes": [
    # {{
      # "name": "scene",
      # "nodes": []
    # }}
  # ],
  # "extensions": {{
    # "BIT_scene_background" : {{
      # "background-uri": "{f}",
      # "rotation": [0, 0.7071067811865475, 0, 0.7071067811865475 ]
    # }}
  # }}
# }}
# """
    # f_handle, gltf_file = mkstemp(suffix=".gltf", prefix="light_")
    # os.close(f_handle)
    # # osp requires the hdr file path to be relative from the gltf file path
    # # (see GLTFData::createLights insg/importer/glTF.cpp, ),
    # # so we have to manipulate pathes a bit...
    # image_relpath = os.path.relpath(image, os.path.dirname(gltf_file))

    # with open(gltf_file, "w") as f:
        # f.write(gltf_snippet.format(f=image_relpath))

    # snippet = """
      # {{
        # "name": "{n}",
        # "type": "IMPORTER",
        # "filename": "{f}"
      # }},"""
    # return snippet.format(n=name, f=gltf_file)


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
    assert material.passthrough.renderer == "Pbrt"
    snippet = material.passthrough.string
    return snippet.format(n=name, c=material.default_color)


def _write_material_glass(name, material):
    """Compute a string in the renderer SDL for a glass material."""
    # TODO
    return ""
    # snippet = """
# type glass
# eta {i}
# attenuationColor {c.r} {c.g} {c.b}
# """
    # return snippet.format(n=name,
                          # c=material.glass.color,
                          # i=material.glass.ior)


def _write_material_disney(name, material):
    """Compute a string in the renderer SDL for a Disney material."""
    # TODO
    return ""
    # # Nota: OSP Principled material does not handle SSS, nor specular tint
    # snippet = """
# type principled
# baseColor {1.r} {1.g} {1.b}
# # No subsurface scattering ({2})
# metallic {3}
# specular {4}
# # No specular tint ({3})
# roughness {6}
# anisotropy {7}
# sheen {8}
# sheenTint {9}
# coat {10}
# coatRoughness {11}
# """
    # return snippet.format(name,
                          # material.disney.basecolor,
                          # material.disney.subsurface,
                          # material.disney.metallic,
                          # material.disney.specular,
                          # material.disney.speculartint,
                          # material.disney.roughness,
                          # material.disney.anisotropic,
                          # material.disney.sheen,
                          # material.disney.sheentint,
                          # material.disney.clearcoat,
                          # 1 - float(material.disney.clearcoatgloss))


def _write_material_diffuse(name, material):
    """Compute a string in the renderer SDL for a Diffuse material."""
    # TODO
    return ""
    # snippet = """
# type obj
# kd {c.r} {c.g} {c.b}
# ns 2
# """
    # return snippet.format(n=name,
                          # c=material.diffuse.color)


def _write_material_mixed(name, material):
    """Compute a string in the renderer SDL for a Mixed material."""
    # TODO
    return ""
    # snippet = """
# type principled
# baseColor {k.r} {k.g} {k.b}
# ior {i}
# transmission {t}
# transmissionColor {c.r} {c.g} {c.b}
# opacity {o}
# """
    # return snippet.format(n=name,
                          # c=material.mixed.glass.color,
                          # i=material.mixed.glass.ior,
                          # k=material.mixed.diffuse.color,
                          # t=material.mixed.transparency,
                          # o=1.0 - material.mixed.transparency)


def _write_material_fallback(name, material):
    """Compute a string in the renderer SDL for a fallback material.

    Fallback material is a simple Diffuse material.
    """
    # TODO
    return ""
    # try:
        # red = float(material.default_color.r)
        # grn = float(material.default_color.g)
        # blu = float(material.default_color.b)
        # assert (0 <= red <= 1) and (0 <= grn <= 1) and (0 <= blu <= 1)
    # except (AttributeError, ValueError, TypeError, AssertionError):
        # red, grn, blu = 1, 1, 1
    # snippet = """
# type obj
# kd {r} {g} {b}
# ns 2
# """
    # return snippet.format(n=name,
                          # r=red,
                          # g=grn,
                          # b=blu)


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
    # Make various adjustments on file:
    # Reorder camera declarations
    with open(project.PageResult, "r") as f:
        template = f.read()

    # Cameras
    pattern =r"(?m)# Camera[\s\S]*?# ~Camera.*$"
    regex_obj = re.compile(pattern)
    camera = str(regex_obj.findall(template)[-1])  # Keep only last camera
    template = camera + '\n' + regex_obj.sub("", template)

    # Set width and height
    template = template.replace("@@WIDTH@@", str(width))
    template = template.replace("@@HEIGHT@@", str(height))

    # Write resulting output to file
    f_handle, f_path = mkstemp(
        prefix=project.Name,
        suffix=os.path.splitext(project.Template)[-1])
    os.close(f_handle)
    with open(f_path, "w") as f:
        f.write(template)
    project.PageResult = f_path
    os.remove(f_path)

    # Build command and launch
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    prefix = params.GetString("Prefix", "")
    if prefix:
        prefix += " "
    rpath = params.GetString("PbrtPath", "")
    args = params.GetString("PbrtParameters", "")
    args += """ --outfile "%s" """ % output
    if not rpath:
        App.Console.PrintError("Unable to locate renderer executable. "
                               "Please set the correct path in "
                               "Edit -> Preferences -> Render\n")
        return ""

    filepath = '"%s"' % project.PageResult

    cmd = prefix + rpath + " " + args + " " + filepath
    App.Console.PrintMessage(cmd+'\n')

    os.system(cmd)

    return output
