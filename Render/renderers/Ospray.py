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
import os.path
import tempfile
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
    matval = material.get_material_values(
        name, _write_texture, _write_value, _write_texref
    )
    # Write the mesh as an OBJ tempfile
    # Direct rotation of mesh is preferred to Placement modification
    # because the latter is buggy (normals are not updated...)
    # tmpmesh.Placement = TRANSFORM.multiply(tmpmesh.Placement)  # Buggy
    mesh.rotate(-pi / 2, 0, 0)  # OK
    basefilename = App.ActiveDocument.getTempFileName(f"{name}_")
    objfile = mesh.write_objfile(
        name,
        objfile=basefilename + ".obj",
        mtlfile=basefilename + ".mtl",
        mtlname="material",
        mtlcontent=_write_material(name, matval),
        normals=False,
    )

    # OBJ is supposed to be in the same directory as final sg file
    filename = os.path.basename(objfile)
    filename = filename.encode("unicode_escape").decode("utf-8")

    snippet_obj = f"""
      {{
        "name": {json.dumps(name)},
        "type": "IMPORTER",
        "filename": {json.dumps(filename)}
      }},"""
    return snippet_obj


def write_camera(name, pos, updir, target, fov):
    """Compute a string in renderer SDL to represent a camera."""
    # OSP camera's default orientation is target=(0, 0, -1), up=(0, 1, 0),
    # in osp coords.
    # Nota: presently (02-19-2021), fov is not managed by osp importer...
    snippet = """
  "camera": {{
    "name": {n},
    "children": [
      {{
        "name": "fovy",
        "type": "PARAMETER",
        "subType": "float",
        "value": {f}
      }}
    ],
    "cameraToWorld": {{
      "affine": [{p.x}, {p.y}, {p.z}],
      "linear": {{
        "x": [{m.A11}, {m.A21}, {m.A31}],
        "y": [{m.A12}, {m.A22}, {m.A32}],
        "z": [{m.A13}, {m.A23}, {m.A33}]
      }}
    }}
  }},"""
    # Final placement in osp = reciprocal(translation*rot*centerTranslation)
    # (see ArcballCamera::setState method in sources)
    plc = TRANSFORM.multiply(pos)

    return snippet.format(
        n=json.dumps(name), p=plc.Base, m=plc.Rotation.toMatrix(), f=fov
    )


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
    # Note: ospray expects a radiance (W/m²), we have to convert power
    # See here: https://www.ospray.org/documentation.html#luminous

    # Write mtl file (material)
    radiance = power / (size_u * size_v)
    radiance /= 1000  # Magic number
    transparency = 1.0 if transparent else 0.0
    mtl = f"""
# Created by FreeCAD <http://www.freecadweb.org>",
newmtl material
type luminous
color {color[0]} {color[1]} {color[2]}
intensity {radiance}
transparency {transparency}
"""

    filebase = App.ActiveDocument.getTempFileName(name + "_")

    mtlfile = f"{filebase}.mtl"
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

    objfile = f"{filebase}.obj"
    with open(objfile, "w", encoding="utf-8") as f:
        f.write(obj)

    # Return SDL
    filename = os.path.basename(objfile)
    filename = filename.encode("unicode_escape").decode("utf-8")
    snippet = f"""
      {{
        "name": {json.dumps(name)},
        "type": "IMPORTER",
        "filename": {json.dumps(filename)}
      }},"""

    return snippet


def write_sunskylight(name, direction, distance, turbidity, albedo):
    """Compute a string in renderer SDL to represent a sunsky light."""
    # We make angle calculations in osp's coordinates system
    # By default, Up is (0,1,0), Right is (1,0,0), and:
    #  - North (0°) is z (0, 0, 1)
    #  - East (90°) is x (1, 0, 0)
    #  - South (180°) is -z (0, 0, -1)
    #  - West (270°) is -x (-1, 0, 0)
    # We'll compute elevation and azimuth accordingly...

    _dir = TRANSFORM.multVec(App.Vector(direction))
    elevation = asin(_dir.y / sqrt(_dir.x**2 + _dir.y**2 + _dir.z**2))
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
                "value": 0.05
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
                "value": [0.0, 1.0, 0.0]
              }},
              {{
                "description": "Right direction",
                "name": "right",
                "sgOnly": true,
                "subType": "vec3f",
                "type": "PARAMETER",
                "value": [1.0, 0.0, 0.0]
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
    gltf_file = App.ActiveDocument.getTempFileName(name + "_") + ".gltf"

    # osp requires the hdr file path to be relative from the gltf file path
    # (see GLTFData::createLights insg/importer/glTF.cpp, ),
    # so we have to manipulate paths a bit...
    image_relpath = os.path.relpath(image, os.path.dirname(gltf_file))

    with open(gltf_file, "w", encoding="utf-8") as f:
        f.write(gltf_snippet.format(f=image_relpath))

    gltf_file = os.path.basename(gltf_file)
    snippet = f"""
      {{
        "name": {json.dumps(name)},
        "type": "IMPORTER",
        "filename": {json.dumps(gltf_file)}
      }},"""
    return snippet


# ===========================================================================
#                              Material implementation
# ===========================================================================


def _write_material(name, matval):
    """Compute a string in the renderer SDL, to represent a material.

    This function should never fail: if the material is not recognized,
    a fallback material is provided.
    """
    try:
        material_function = MATERIALS[matval.shadertype]
    except KeyError:
        msg = (
            "'{}' - Material '{}' unknown by renderer, using fallback "
            "material\n"
        )
        App.Console.PrintWarning(msg.format(name, matval.shadertype))
        snippet_mat = _write_material_fallback(name, matval.default_color)
    else:
        snippet_mat = [
            material_function(name, matval),
            matval.write_textures(),
        ]
        snippet_mat = "".join(snippet_mat)

    return snippet_mat


def _write_material_passthrough(name, matval):
    """Compute a string in the renderer SDL for a passthrough material."""
    snippet = "\n" + matval["string"]
    return snippet.format(n=name, c=matval.default_color)


def _write_material_glass(name, matval):  # pylint: disable=unused-argument
    """Compute a string in the renderer SDL for a glass material."""
    snippet = f"""
type principled
{matval["ior"]}
{matval["color"]}
transmission 1
specular 1
metallic 0
diffuse 0
opacity 1
"""
    return snippet


def _write_material_disney(name, matval):  # pylint: disable=unused-argument
    """Compute a string in the renderer SDL for a Disney material."""
    # Nota1: OSP Principled material does not handle SSS, nor specular tint
    # Nota2: if metallic is set, specular should be 1.0. See here:
    # https://github.com/ospray/ospray_studio/issues/5
    snippet = f"""
type principled
{matval["basecolor"]}
# No subsurface scattering (Ospray limitation)
{matval["metallic"]}
{matval["specular"]}
# No specular tint (Ospray limitation)
{matval["roughness"]}
{matval["anisotropic"]}
{matval["sheen"]}
{matval["sheentint"]}
{matval["clearcoat"]}
{matval["clearcoatgloss"]}
{matval["normal"]}
"""
    return snippet


def _write_material_diffuse(name, matval):  # pylint: disable=unused-argument
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet = f"""
type principled
{matval["color"]}
metallic 0
specular 0
diffuse 1
"""
    return snippet


def _write_material_mixed(name, matval):
    """Compute a string in the renderer SDL for a Mixed material."""
    # Glass
    submat_g = matval.getmixedsubmat("glass", name + "_glass")
    snippet_g_tex = submat_g.write_textures()

    # Diffuse
    submat_d = matval.getmixedsubmat("diffuse", name + "_diffuse")
    snippet_d_tex = submat_d.write_textures()

    transparency = matval.material.mixed.transparency
    assert isinstance(transparency, float)

    snippet_mix = f"""
type principled
{submat_d["color"]}
{submat_g["ior"]}
transmission {transparency}
{submat_g["color"]}
opacity {1 - transparency}
specular 0.5
"""
    snippet = [snippet_mix, snippet_d_tex, snippet_g_tex]
    return "".join(snippet)


def _write_material_carpaint(name, matval):  # pylint: disable=unused-argument
    """Compute a string in the renderer SDL for a carpaint material."""
    snippet = f"""
type carPaint
{matval["basecolor"]}
"""
    return snippet


def _write_material_fallback(name, matval):
    """Compute a string in the renderer SDL for a fallback material.

    Fallback material is a simple Diffuse material.
    """
    try:
        red = float(matval.material.color.r)
        grn = float(matval.material.color.g)
        blu = float(matval.material.color.b)
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
    "Carpaint": _write_material_carpaint,
}


# ===========================================================================
#                              Textures
# ===========================================================================

# Field mapping from internal materials to OBJ ones (only for non trivial)
# None will exclude
_FIELD_MAPPING = {
    ("Diffuse", "color"): "baseColor",
    ("Diffuse", "bump"): None,
    ("Diffuse", "displacement"): None,
    ("Disney", "basecolor"): "baseColor",
    ("Disney", "subsurface"): "",
    ("Disney", "speculartint"): "",
    ("Disney", "anisotropic"): "anisotropy",
    ("Disney", "sheentint"): "sheenTint",
    ("Disney", "clearcoat"): "coat",
    ("Disney", "clearcoatgloss"): "coatRoughness",
    ("Disney", "bump"): None,
    ("Disney", "displacement"): None,
    ("Glass", "color"): "transmissionColor",
    ("Glass", "ior"): "ior",
    ("Glass", "bump"): None,
    ("Glass", "displacement"): None,
    ("Carpaint", "basecolor"): "baseColor",
    ("Mixed", "transparency"): "transmission",
    ("Mixed", "diffuse"): "",
    ("Mixed", "shader"): "",
    ("Mixed", "glass"): "",
    ("Mixed", "bump"): None,
    ("Mixed", "displacement"): None,
    ("glass", "color"): "transmissionColor",
    ("diffuse", "color"): "baseColor",
    ("Passthrough", "string"): "",
    ("Passthrough", "renderer"): "",
}


def _write_texture(**kwargs):
    """Compute a string in renderer SDL to describe a texture.

    The texture is computed from a property of a shader (as the texture is
    always integrated into a shader). Property's data are expected as
    arguments.

    Args:
        objname -- Object name for which the texture is computed
        propname -- Name of the shader property
        propvalue -- Value of the shader property

    Returns:
        the name of the texture
        the SDL string of the texture
    """
    # Retrieve material parameters
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    propvalue = kwargs["propvalue"]
    objname = kwargs["objname"]

    # Get texture parameters
    filename = os.path.basename(propvalue.file)
    scale, rotation = float(propvalue.scale), float(propvalue.rotation)
    translation_u = float(propvalue.translation_u)
    translation_v = float(propvalue.translation_v)

    field = _FIELD_MAPPING.get((shadertype, propname), propname)

    # Exclusions (not supported)
    if field is None:
        return propname, ""
    if propname in [
        "clearcoatgloss",
        "ior",
        "subsurface",
        "speculartint",
        "bump",
        "displacement",
    ]:
        msg = (
            f"[Render] [Ospray] [{objname}] Warning: texture for "
            f"'{shadertype}::{propname}' "
            f"is not supported by Ospray. Falling back to default value.\n"
        )
        App.Console.PrintWarning(msg)
        return propname, ""

    # Snippets for texref
    if proptype in ["RGB", "float", "texonly"]:
        tex = [
            f"# Texture {field}",
            f"map_{field} {filename}",
            f"map_{field}.rotation {rotation}",
            f"map_{field}.scale {scale} {scale}",
            f"map_{field}.translation {translation_u} {translation_v}",
        ]
        tex = "\n".join(tex)
    elif proptype == "node":
        tex = ""
    else:
        raise NotImplementedError

    return propname, tex


def _write_value(**kwargs):
    """Compute a string in renderer SDL from a shader property value.

    Args:
        proptype -- Shader property's type
        propvalue -- Shader property's value

    The result depends on the type of the value...
    """
    # Retrieve parameters
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    val = kwargs["propvalue"]
    objname = kwargs["objname"]

    field = _FIELD_MAPPING.get((shadertype, propname), propname)

    # Exclusions
    if field is None:
        msg = (
            f"[Render] [Ospray] [{objname}] Warning: "
            f"'{shadertype}::{propname}' is not supported by Ospray. "
            f"Skipping...\n"
        )
        App.Console.PrintWarning(msg)
        return ""

    # Special cases
    if propname == "clearcoatgloss":
        val = 1 - val

    # Snippets for values
    if proptype == "RGB":
        value = f"{field} {val.r:.8} {val.g:.8} {val.b:.8}"
    elif proptype == "float":
        value = f"{field} {val:.8}"
    elif proptype == "node":
        value = ""
    elif proptype == "RGBA":
        value = f"{field} {val.r:.8} {val.g:.8} {val.b:.8} {val.a:.8}"
    elif proptype == "str":
        value = f"{field} {val}"
    else:
        raise NotImplementedError

    return value


def _write_texref(**kwargs):
    """Compute a string in SDL for a reference to a texture in a shader."""
    # Retrieve parameters
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    objname = kwargs["objname"]

    field = _FIELD_MAPPING.get((shadertype, propname), propname)

    # Exclusions
    if field is None:
        msg = (
            f"[Render] [Ospray] [{objname}] Warning: "
            f"'{shadertype}::{propname}' is not supported by Ospray. "
            f"Skipping...\n"
        )
        App.Console.PrintWarning(msg)
        return ""
    if propname in ["clearcoatgloss", "ior"]:
        return f"{field} 1.5" if propname == "ior" else f"{field} 1.0"

    # Snippets for values
    if proptype == "RGB":
        value = f"{field} 1.0 1.0 1.0"
    elif proptype == "float":
        value = f"{field} 1.0"
    elif proptype == "node":
        value = f"{field} 1.0"
    elif proptype == "RGBA":
        value = f"{field} 1.0 1.0 1.0 1.0"
    elif proptype == "texonly":
        value = f"{field} 4.0" if propname == "normal" else f"{field} 1.0"
    else:
        raise NotImplementedError

    return value


# ===========================================================================
#                              Render function
# ===========================================================================


def render(project, prefix, external, output, width, height):
    """Generate renderer command.

    Args:
        project -- The project to render
        prefix -- A prefix string for call (will be inserted before path to
            renderer)
        external -- A boolean indicating whether to call UI (true) or console
            (false) version of renderder
        width -- Rendered image width, in pixels
        height -- Rendered image height, in pixels

    Returns:
        The command to run renderer (string)
        A path to output image file (string)
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

    # Write reformatted input to file
    f_handle, f_path = tempfile.mkstemp(
        prefix=project.Name, suffix=os.path.splitext(project.Template)[-1]
    )
    os.close(f_handle)
    with open(f_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(json_load, indent=2))
    project.PageResult = f_path
    os.remove(f_path)

    # Prepare osp output file
    # Osp renames the output file when writing, so we have to ask it to write a
    # specific file but we'll return the actual file written (we recompute the
    # name)
    # Nota: as a consequence, we cannot take user choice for output file into
    # account
    outfile_for_osp = os.path.join(tempfile.gettempdir(), "ospray_out")
    outfile_actual = f"{outfile_for_osp}.0000.png"  # The file that osp'll use
    # We remove the outfile before writing, otherwise ospray will choose
    # another file
    try:
        os.remove(outfile_actual)
    except FileNotFoundError:
        # The file does not already exist: no problem
        pass

    # Build command and launch
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    prefix = params.GetString("Prefix", "")
    if prefix:
        prefix += " "
    rpath = params.GetString("OspPath", "")
    args = params.GetString("OspParameters", "")
    if output:
        args += "  --image " + outfile_for_osp
    if not rpath:
        App.Console.PrintError(
            "Unable to locate renderer executable. "
            "Please set the correct path in "
            "Edit -> Preferences -> Render\n"
        )
        return None, None

    cmd = prefix + rpath + " " + args + " " + f'"{project.PageResult}"'

    # Note: at the moment (08-20-2022), width, height, background are
    # not managed by osp

    return cmd, outfile_actual
