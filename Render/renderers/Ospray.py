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
#
# Please note coordinate systems are different between fcd and osp:
#
# FreeCAD (z is up):         Ospray (y is up):
#
#
#  z  y                         y
#  | /                          |
#  .--x                         .--x
#                              /
#                             z
#

import json
import os
import shlex
from subprocess import Popen
from tempfile import mkstemp
from math import degrees, asin, sqrt, atan2, pi

import FreeCAD as App

# Transformation matrix from fcd coords to osp coords
TRANSFORM = App.Placement(
    App.Matrix(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1)
)

TEMPLATE_FILTER = "Ospray templates (ospray_*.sg)"

# ===========================================================================
#                             Write functions
# ===========================================================================


def write_mesh(name, mesh, material):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""
    # Write the mesh as an OBJ tempfile
    f_handle, objfile = mkstemp(suffix=".obj", prefix="_")
    os.close(f_handle)
    tmpmesh = mesh.copy()
    # Direct rotation of mesh is preferred to Placement modification
    # because the latter is buggy (normals are not updated...)
    # tmpmesh.Placement = TRANSFORM.multiply(tmpmesh.Placement)  # Buggy
    tmpmesh.rotate(-pi / 2, 0, 0)  # OK
    tmpmesh.write(objfile)

    # Fix missing object name in OBJ file (mandatory)
    # We want to insert a 'o ...' statement before the first 'f ...'
    # We add also a 'usemtl' statement
    with open(objfile, "r", encoding="utf-8") as f:
        buffer = f.readlines()

    i = next(i for i, l in enumerate(buffer) if l.startswith("f "))
    buffer.insert(i, f"o {name}\nusemtl material\n")

    # Write material
    f_handle, mtlfile = mkstemp(suffix=".mtl", prefix="_")
    os.close(f_handle)
    mtl = "newmtl material" + _write_material(name, material)
    with open(mtlfile, "w", encoding="utf-8") as f:
        f.write(mtl)

    buffer.insert(0, f"mtllib {os.path.basename(mtlfile)}\n")

    with open(objfile, "w", encoding="utf-8") as f:
        f.write("".join(buffer))

    snippet_obj = """
      {{
        "name": {n},
        "type": "IMPORTER",
        "filename": {f}
      }},"""
    filename = objfile.encode("unicode_escape").decode("utf-8")
    return snippet_obj.format(n=json.dumps(name), f=json.dumps(filename))


def write_camera(name, pos, updir, target, fov):
    """Compute a string in renderer SDL to represent a camera."""
    # OSP camera's default orientation is target=(0, 0, -1), up=(0, 1, 0),
    # in osp coords.
    # Nota: presently (02-19-2021), fov is not managed by osp importer...
    snippet = """
  "camera": {{
    "name": {n},
    "centerTranslation": {{
      "affine": [0.0, 0.0, 0.0],
      "linear": {{
        "x": [1.0, 0.0, 0.0],
        "y": [0.0, 1.0, 0.0],
        "z": [0.0, 0.0, 1.0]
      }}
    }},
    "rotation": {{"i": {r[0]}, "j": {r[1]}, "k": {r[2]}, "r": {r[3]}}},
    "translation": {{
      "affine": [{p.x}, {p.y}, {p.z}],
      "linear": {{
        "x": [1.0, 0.0, 0.0],
        "y": [0.0, 1.0, 0.0],
        "z": [0.0, 0.0, 1.0]
      }}
    }}
  }},"""

    # Final placement in osp = reciprocal(translation*rot*centerTranslation)
    # (see ArcballCamera::setState method in sources)
    plc = TRANSFORM.multiply(pos)
    plc = plc.inverse()

    return snippet.format(n=json.dumps(name), p=plc.Base, r=plc.Rotation.Q)


def write_pointlight(name, pos, color, power):
    """Compute a string in renderer SDL to represent a point light."""
    # Tip: in studio, to visualize where the light is, increase the radius

    snippet = """
      {{
        "name": "lights",
        "type": "LIGHTS",
        "subType": "lights",
        "children": [
          {{
            "name": {n},
            "type": "LIGHT",
            "subType": "sphere",
            "children": [
              {{
                "name": "visible",
                "description": "whether the light can be seen directly",
                "sgOnly": false,
                "subType": "bool",
                "type": "PARAMETER",
                "value": true
              }},
              {{
                "name": "intensity",
                "description": "intensity of the light (a factor)",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": {s}
              }},
              {{
                "name": "color",
                "description": "color of the light",
                "sgOnly": false,
                "subType": "rgb",
                "type": "PARAMETER",
                "value": [{c[0]}, {c[1]}, {c[2]}]
              }},
              {{
                "name": "position",
                "description": "position of the light",
                "sgOnly": false,
                "subType": "vec3f",
                "type": "PARAMETER",
                "value": [{p[0]}, {p[1]}, {p[2]}]
              }}
            ]
          }}
        ]
      }},"""
    osp_pos = TRANSFORM.multVec(pos)
    return snippet.format(n=json.dumps(name), c=color, p=osp_pos, s=power)


def write_arealight(name, pos, size_u, size_v, color, power, transparent):
    """Compute a string in renderer SDL to represent an area light."""
    # Write mtl file (material)
    power /= 10
    transparency = 1.0 if transparent else 0.0
    mtl = f"""
# Created by FreeCAD <http://www.freecadweb.org>",
newmtl material
type luminous
color {color[0]} {color[1]} {color[2]}
intensity {power}
transparency {transparency}
"""

    f_handle, mtlfile = mkstemp(suffix=".mtl", prefix="light_")
    os.close(f_handle)
    with open(mtlfile, "w", encoding="utf-8") as f:
        f.write(mtl)

    # Write obj file (geometry)
    osp_pos = TRANSFORM.multiply(pos)
    verts = [
        (-size_u, -size_v, 0),
        (+size_u, -size_v, 0),
        (+size_u, +size_v, 0),
        (-size_u, +size_v, 0),
    ]
    verts = [osp_pos.multVec(App.Vector(*v)) for v in verts]
    verts = [f"v {v.x} {v.y} {v.z}" for v in verts]
    verts = "\n".join(verts)
    normal = osp_pos.multVec(App.Vector(0, 0, 1))

    obj = f"""
# Created by FreeCAD <http://www.freecadweb.org>"]
mtllib {os.path.basename(mtlfile)}
{verts}
vn {normal.x} {normal.y} {normal.z}
o {name}
usemtl material
f 1//1 2//1 3//1 4//1
"""

    f_handle, objfile = mkstemp(suffix=".obj", prefix="light_")
    os.close(f_handle)
    with open(objfile, "w", encoding="utf-8") as f:
        f.write(obj)

    # Return SDL
    filename = objfile.encode("unicode_escape").decode("utf-8")
    snippet = """
      {{
        "name": {n},
        "type": "IMPORTER",
        "filename": {f}
      }},"""

    return snippet.format(n=json.dumps(name), f=json.dumps(filename))


def write_sunskylight(name, direction, distance, turbidity, albedo):
    """Compute a string in renderer SDL to represent a sunsky light."""
    # We make angle calculations in ocp's coordinates system
    # By default, Up is (0,1,0), Right is (1,0,0), and:
    #  - North (0°) is z (0, 0, 1)
    #  - East (90°) is x (1, 0, 0)
    #  - South (180°) is -z (0, 0, -1)
    #  - West (270°) is -x (-1, 0, 0)
    # We'll compute elevation and azimuth accordingly...

    _dir = TRANSFORM.multVec(App.Vector(direction))
    elevation = asin(_dir.y / sqrt(_dir.x ** 2 + _dir.y ** 2 + _dir.z ** 2))
    azimuth = atan2(_dir.x, _dir.z)
    snippet = """
      {{
        "description": "Lights",
        "name": "lights",
        "subType": "lights",
        "type": "LIGHTS",
        "children": [
          {{
            "name": {n},
            "description": "Sunsky light",
            "type": "LIGHT",
            "subType": "sunSky",
            "children": [
              {{
                "description": "whether the light can be seen directly",
                "name": "visible",
                "sgOnly": false,
                "subType": "bool",
                "type": "PARAMETER",
                "value": true
              }},
              {{
                "description": "intensity of the light (a factor)",
                "name": "intensity",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": 1.0
              }},
              {{
                "description": "color of the light",
                "name": "color",
                "sgOnly": false,
                "subType": "rgb",
                "type": "PARAMETER",
                "value": [1.0, 1.0, 1.0]
              }},
              {{
                "description": "OSPRay light type",
                "name": "type",
                "sgOnly": true,
                "subType": "string",
                "type": "PARAMETER",
                "value": "sunSky"
              }},
              {{
                "description": "Up direction",
                "name": "up",
                "sgOnly": false,
                "subType": "vec3f",
                "type": "PARAMETER",
                "value": [0,1,0]
              }},
              {{
                "description": "Right direction",
                "name": "right",
                "sgOnly": true,
                "subType": "vec3f",
                "type": "PARAMETER",
                "value": [1,0,0]
              }},
              {{
                "description": "Angle to horizon",
                "name": "elevation",
                "sgOnly": true,
                "subType": "float",
                "type": "PARAMETER",
                "value": {e}
              }},
              {{
                "description": "Angle to North",
                "name": "azimuth",
                "sgOnly": true,
                "subType": "float",
                "type": "PARAMETER",
                "value": {a}
              }},
              {{
                "description": "Turbidity",
                "name": "turbidity",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": {t}
              }},
              {{
                "description": "Ground albedo",
                "name": "albedo",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": {g}
              }}
            ]
          }}
        ]
      }},"""
    return snippet.format(
        n=json.dumps(name),
        t=turbidity,
        e=degrees(elevation),
        a=degrees(azimuth),
        g=albedo,
    )


def write_imagelight(name, image):
    """Compute a string in renderer SDL to represent an image-based light."""
    # At this time (02-15-2021), in current version (0.6.0),
    # texture import is not serviceable in OspStudio - see here:
    # https://github.com/ospray/ospray_studio/blob/release-0.6.x/sg/JSONDefs.h#L107
    # As a workaround, we use a gltf file...

    gltf_snippet = """
{{
  "asset": {{
    "generator": "FreeCAD Render Workbench",
    "version": "2.0"
  }},
  "scene": 0,
  "scenes": [
    {{
      "name": "scene",
      "nodes": []
    }}
  ],
  "extensions": {{
    "BIT_scene_background" : {{
      "background-uri": "{f}",
      "rotation": [0, 0.7071067811865475, 0, 0.7071067811865475 ]
    }}
  }}
}}
"""
    f_handle, gltf_file = mkstemp(suffix=".gltf", prefix="light_")
    os.close(f_handle)
    # osp requires the hdr file path to be relative from the gltf file path
    # (see GLTFData::createLights insg/importer/glTF.cpp, ),
    # so we have to manipulate pathes a bit...
    image_relpath = os.path.relpath(image, os.path.dirname(gltf_file))

    with open(gltf_file, "w", encoding="utf-8") as f:
        f.write(gltf_snippet.format(f=image_relpath))

    snippet = """
      {{
        "name": {n},
        "type": "IMPORTER",
        "filename": {f}
      }},"""
    return snippet.format(n=json.dumps(name), f=json.dumps(gltf_file))


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
        msg = (
            "'{}' - Material '{}' unknown by renderer, using fallback "
            "material\n"
        )
        App.Console.PrintWarning(msg.format(name, material.shadertype))
        snippet_mat = _write_material_fallback(name, material.default_color)
    return snippet_mat


def _write_material_passthrough(name, material):
    """Compute a string in the renderer SDL for a passthrough material."""
    assert material.passthrough.renderer == "Ospray"
    snippet = "\n" + material.passthrough.string
    return snippet.format(n=name, c=material.default_color)


def _write_material_glass(name, material):
    """Compute a string in the renderer SDL for a glass material."""
    snippet = """
type glass
eta {i}
attenuationColor {c.r} {c.g} {c.b}
"""
    return snippet.format(n=name, c=material.glass.color, i=material.glass.ior)


def _write_material_disney(name, material):
    """Compute a string in the renderer SDL for a Disney material."""
    # Nota1: OSP Principled material does not handle SSS, nor specular tint
    # Nota2: if metallic is set, specular should be 1.0. See here:
    # https://github.com/ospray/ospray_studio/issues/5
    snippet = """
type principled
baseColor {1.r} {1.g} {1.b}
# No subsurface scattering ({2})
metallic {3}
specular {4}
# No specular tint ({3})
roughness {6}
anisotropy {7}
sheen {8}
sheenTint {9}
coat {10}
coatRoughness {11}
"""
    return snippet.format(
        name,
        material.disney.basecolor,
        material.disney.subsurface,
        material.disney.metallic,
        material.disney.specular if not material.disney.metallic else 1.0,
        material.disney.speculartint,
        material.disney.roughness,
        material.disney.anisotropic,
        material.disney.sheen,
        material.disney.sheentint,
        material.disney.clearcoat,
        1 - float(material.disney.clearcoatgloss),
    )


def _write_material_diffuse(name, material):
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet = """
type obj
kd {c.r} {c.g} {c.b}
ns 2
"""
    return snippet.format(n=name, c=material.diffuse.color)


def _write_material_mixed(name, material):
    """Compute a string in the renderer SDL for a Mixed material."""
    snippet = """
type principled
baseColor {k.r} {k.g} {k.b}
ior {i}
transmission {t}
transmissionColor {c.r} {c.g} {c.b}
opacity {o}
"""
    return snippet.format(
        n=name,
        c=material.mixed.glass.color,
        i=material.mixed.glass.ior,
        k=material.mixed.diffuse.color,
        t=material.mixed.transparency,
        o=1.0 - material.mixed.transparency,
    )


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
type obj
kd {r} {g} {b}
ns 2
"""
    return snippet.format(n=name, r=red, g=grn, b=blu)


MATERIALS = {
    "Passthrough": _write_material_passthrough,
    "Glass": _write_material_glass,
    "Disney": _write_material_disney,
    "Diffuse": _write_material_diffuse,
    "Mixed": _write_material_mixed,
}


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
    # Move cameras up to root node
    cameras = ["\n"]
    result = []
    with open(project.PageResult, "r", encoding="utf8") as f:
        for line in f:
            if '"camera"' in line:
                cameras += line
                nbr = line.count("{") - line.count("}")
                for line2 in f:
                    cameras += line2
                    nbr += line2.count("{") - line2.count("}")
                    if not nbr:
                        break
            else:
                result += line
        result[2:2] = cameras
        result = "".join(result)

    # Merge light groups
    json_load = json.loads(result)
    world_children = json_load["world"]["children"]
    world_children.sort(key=lambda x: x["type"] == "LIGHTS")  # Lights last
    lights = []

    def remaining_lightgroups():
        try:
            child = world_children[-1]
        except IndexError:
            return False
        return child["type"] == "LIGHTS"

    while remaining_lightgroups():
        light = world_children.pop()
        lights += light["children"]
    lightsmanager_children = json_load["lightsManager"]["children"]
    lightsmanager_children.extend(lights)

    # Write resulting output to file
    f_handle, f_path = mkstemp(
        prefix=project.Name, suffix=os.path.splitext(project.Template)[-1]
    )
    os.close(f_handle)
    with open(f_path, "w", encoding="utf-8") as f:
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
    if not rpath:
        App.Console.PrintError(
            "Unable to locate renderer executable. "
            "Please set the correct path in "
            "Edit -> Preferences -> Render\n"
        )
        return ""

    cmd = prefix + rpath + " " + args + " " + f'"{project.PageResult}"'
    App.Console.PrintMessage(cmd + "\n")

    # Note: at the moment (02-19-2021), width, height, output, background are
    # not managed by osp

    try:
        Popen(shlex.split(cmd))
    except OSError as err:
        App.Console.PrintError(f"OspStudio call failed: '{err.strerror}'\n")

    return None
