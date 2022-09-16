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

import os
import re
from tempfile import mkstemp

import FreeCAD as App

# Transformation matrix from fcd coords to osp coords
TRANSFORM = App.Placement(
    App.Matrix(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1)
)

TEMPLATE_FILTER = "Pbrt templates (pbrt_*.pbrt)"

# ===========================================================================
#                             Write functions
# ===========================================================================


def write_mesh(name, mesh, material):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""
    matval = material.get_material_values(
        name, _write_texture, _write_value, _write_texref
    )
    material = _write_material(name, matval)
    pnts = [f"{p.x} {p.y} {p.z}" for p in mesh.Topology[0]]
    inds = [f"{i[0]} {i[1]} {i[2]}" for i in mesh.Topology[1]]
    pnts = "  ".join(pnts)
    inds = "  ".join(inds)
    if mesh.has_uvmap():
        uvs = [f"{t.x} {t.y}" for t in mesh.uvmap]
        uvs = "  ".join(uvs)
        uvs = f"""    "point2 uv" [ {uvs} ]\n"""
    else:
        uvs = ""

    snippet = f"""# Object '{name}'
AttributeBegin
{matval.write_textures()}
{material}
  Shape "trianglemesh"
    "point3 P" [ {pnts} ]
    "integer indices" [ {inds} ]
{uvs}
AttributeEnd
# ~Object '{name}'
"""
    return snippet


def write_camera(name, pos, updir, target, fov):
    """Compute a string in renderer SDL to represent a camera."""
    snippet = """# Camera '{n}'
Scale -1 1 1
LookAt {p.x} {p.y} {p.z}
       {t.x} {t.y} {t.z}
       {u.x} {u.y} {u.z}
Camera "perspective" "float fov" {f}
# ~Camera '{n}'
"""  # NB: do not modify enclosing comments in snippet
    return snippet.format(n=name, p=pos.Base, t=target, u=updir, f=fov)


def write_pointlight(name, pos, color, power):
    """Compute a string in renderer SDL to represent a point light."""
    snippet = """# Pointlight '{n}'
AttributeBegin
  LightSource "point"
    "rgb I" [{c[0]} {c[1]} {c[2]}]
    "point3 from" [{o.x} {o.y} {o.z}]
    "float scale" [{s}]
AttributeEnd
# ~Pointlight '{n}'
"""
    return snippet.format(n=name, o=pos, c=color, s=power)


def write_arealight(name, pos, size_u, size_v, color, power, transparent):
    """Compute a string in renderer SDL to represent an area light."""
    points = [
        (-size_u / 2, -size_v / 2, 0),
        (+size_u / 2, -size_v / 2, 0),
        (+size_u / 2, +size_v / 2, 0),
        (-size_u / 2, +size_v / 2, 0),
    ]
    points = [pos.multVec(App.Vector(*p)) for p in points]
    points = [f"{p.x} {p.y} {p.z}" for p in points]
    points = "  ".join(points)

    power *= 100

    snippet = """# Arealight '{n}'
AttributeBegin
  AreaLightSource "diffuse"
    "rgb L" [{c[0]} {c[1]} {c[2]}]
    "bool twosided" true
    "float scale" [{s}]
  Shape "trianglemesh"
    "integer indices" [0 1 2  0 2 3]
    "point3 P" [{p}]
AttributeEnd
# ~Arealight '{n}'
"""
    return snippet.format(n=name, c=color, s=power, p=points)


def write_sunskylight(name, direction, distance, turbidity, albedo):
    """Compute a string in renderer SDL to represent a sunsky light."""
    # As pbrt does not provide an integrated support for sun-sky lighting
    # (like Hosek-Wilkie e.g.), so we just use an bluish infinite light
    # and a white distant light...
    direction = -direction
    snippet = """# Sun-sky light '{n}'
AttributeBegin
  LightSource "infinite"
    "rgb L" [0.53 0.81 0.92]
    "float scale" 0.5
  LightSource "distant"
    "blackbody L" [6500]
    "float scale" 4
    "point3 from" [0 0 0]
    "point3 to" [{d.x} {d.y} {d.z}]
AttributeEnd
# ~Sun-sky light '{n}'\n"""
    return snippet.format(n=name, d=direction)


def write_imagelight(name, image):
    """Compute a string in renderer SDL to represent an image-based light."""
    # Caveat: pbrt just accepts square images...
    snippet = """# Imagelight '{n}'
AttributeBegin
    LightSource "infinite" "string filename" "{m}"
AttributeEnd
# ~Imagelight '{n}'\n"""
    return snippet.format(n=name, m=image)


# ===========================================================================
#                              Material implementation
# ===========================================================================


def _write_material(name, matval):
    """Compute a string in the renderer SDL, to represent a material.

    This function should never fail: if the material is not recognized,
    a fallback material is provided.
    """
    try:
        write_function = MATERIALS[matval.shadertype]
    except KeyError:
        msg = (
            "'{}' - Material '{}' unknown by renderer, using fallback "
            "material\n"
        )
        App.Console.PrintWarning(msg.format(name, matval.shadertype))
        write_function = _write_material_fallback
    snippet_mat = write_function(name, matval)
    return snippet_mat


def _write_material_passthrough(name, matval):
    """Compute a string in the renderer SDL for a passthrough material."""
    snippet = "# Passthrough\n" + matval["string"] + "\n"
    return snippet.format(n=name, c=matval.default_color)


def _write_material_glass(name, matval):
    """Compute a string in the renderer SDL for a glass material."""
    snippet = f"""  # Material '{name}'
  Material "dielectric"
{matval["ior"]}"""
    return snippet


def _write_material_disney(name, matval):
    """Compute a string in the renderer SDL for a Disney material."""
    # Disney is no more supported in pbrt v4 (in contrast to pbrt v3), so this
    # function will not compute anything...
    # pylint: disable=unused-argument
    return ""


def _write_material_diffuse(name, matval):
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet = f"""  # Material '{name}'
  Material "diffuse"
{matval["color"]}"""
    return snippet


def _write_material_mixed(name, material):
    """Compute a string in the renderer SDL for a Mixed material."""
    snippet = """  # Material '{n}'
  MakeNamedMaterial "{n}_1"
    "string type" "diffuse"
    "rgb reflectance" [{c.r} {c.g} {c.b}]
  MakeNamedMaterial "{n}_2"
    "string type" "dielectric"
    "float eta" {i}
  Material "mix"
    "string materials" ["{n}_1" "{n}_2"]
    "float amount" {r}
"""
    return snippet.format(
        n=name,
        c=material.mixed.glass.color,
        i=material.mixed.glass.ior,
        k=material.mixed.diffuse.color,
        r=material.mixed.transparency,
    )


def _write_material_carpaint(name, matval):
    """Compute a string in the renderer SDL for a carpaint material."""
    snippet = f"""  # Material '{name}'
  Material "coateddiffuse"
{matval["basecolor"]}
    "float roughness" [ 0.0 ]
    "float eta" [ 1.54 ]"""
    return snippet


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
    snippet = """  # Material '{n}' -- fallback
  Material "diffuse"
    "rgb reflectance" [{r} {g} {b}]
"""
    return snippet.format(n=name, r=red, g=grn, b=blu)


MATERIALS = {
    "Passthrough": _write_material_passthrough,
    "Glass": _write_material_glass,
    # "Disney": _write_material_disney,  -- NOT SUPPORTED BY PBRT V4
    "Diffuse": _write_material_diffuse,
    "Mixed": _write_material_mixed,
    "Carpaint": _write_material_carpaint,
}


# ===========================================================================
#                            Texture management
# ===========================================================================


def _texname(objname, propvalue):
    """Compute texture name (helper).

    For a texture name common to _write_texture and _write_texref.
    """
    return f"{objname}_{propvalue.name}_{propvalue.subname}"


def _write_texture(**kwargs):
    """Compute a string in renderer SDL to describe a texture.

    Returns:
        the name of the texture
        the SDL string of the texture
    """
    # Retrieve parameters
    objname = kwargs["objname"]
    propname = kwargs["propname"]
    proptype = kwargs["proptype"]
    propvalue = kwargs["propvalue"]

    # Compute texture parameters
    texname = _texname(objname, propvalue)
    scale = 1 / propvalue.scale if propvalue.scale != 0.0 else 1.0
    textype, encoding = (
        ("spectrum", "sRGB") if proptype == "RGB" else ("float", "linear")
    )
    filebasename = os.path.basename(propvalue.file)

    # Compute snippet
    snippet = f"""
  Texture "{texname}" "{textype}" "imagemap"
    "string filename" "{filebasename}"
    "string mapping" "uv"
    "string encoding" "{encoding}"
    "float uscale" {scale}
    "float vscale" {scale}
    "float udelta" {propvalue.translation_u}
    "float vdelta" {propvalue.translation_v}
"""

    return texname, snippet


_VALSNIPPETS = {
    "RGB": '    "rgb {field}" [{val.r} {val.g} {val.b}]\n',
    "float": '    "float {field}" {val}\n',
    "node": "",
    "texonly": "{val}",
    "str": "{val}",
}

# TODO
_FIELD_MAPPING = {
    ("Diffuse", "color"): "reflectance",
    ("Glass", "ior"): "eta",
    ("Carpaint", "basecolor"): "reflectance",
}


def _write_value(**kwargs):
    """Compute a string in renderer SDL from a shader property value.

    Args:
        proptype -- Shader property's type
        propvalue -- Shader property's value

    The result depends on the type of the value...
    """
    # Retrieve parameters
    proptype = kwargs["proptype"]
    propvalue = kwargs["propvalue"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]

    # Field name
    field = _FIELD_MAPPING.get((shadertype, propname), propname)

    # Snippet for values
    snippet = _VALSNIPPETS[proptype]
    value = snippet.format(field=field, val=propvalue)
    return value


def _write_texref(**kwargs):
    """Compute a string in SDL for a reference to a texture in a shader."""
    # Retrieve parameters
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    objname = kwargs["objname"]
    propvalue = kwargs["propvalue"]

    # Field name
    field = _FIELD_MAPPING.get((shadertype, propname), propname)

    # Exclusions
    if propname == "ior":
        msg = (
            "[Render] [Pbrt] WARNING - pbrt does not support texture for "
            "ior. Falling back to default constant value (1.5)\n"
        )
        App.Console.PrintWarning(msg)
        return ""

    # Texture name
    texname = _texname(objname, propvalue)

    # Snippet for texref
    snippet = f"""    "texture {field}" "{texname}"\n"""

    return snippet


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
    # Make various adjustments on file:
    # Reorder camera declarations and set width/height
    with open(project.PageResult, "r", encoding="utf-8") as f:
        template = f.read()

    # Cameras
    pattern = r"(?m)# Camera[\s\S]*?# ~Camera.*$"
    regex_obj = re.compile(pattern)
    camera = str(regex_obj.findall(template)[-1])  # Keep only last camera
    template = camera + "\n" + regex_obj.sub("", template)

    # Set width and height
    template = template.replace("@@WIDTH@@", str(width))
    template = template.replace("@@HEIGHT@@", str(height))

    # Write resulting output to file
    f_handle, f_path = mkstemp(
        prefix=project.Name, suffix=os.path.splitext(project.Template)[-1]
    )
    os.close(f_handle)
    with open(f_path, "w", encoding="utf-8") as f:
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
    args += f' --outfile "{output}" '
    if not rpath:
        App.Console.PrintError(
            "Unable to locate renderer executable. "
            "Please set the correct path in "
            "Edit -> Preferences -> Render\n"
        )
        return None, None

    filepath = f'"{project.PageResult}"'

    cmd = prefix + rpath + " " + args + " " + filepath

    return cmd, output
