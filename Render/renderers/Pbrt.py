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
import math
import itertools
import textwrap

import FreeCAD as App

# Transformation matrix from fcd coords to osp coords
TRANSFORM = App.Placement(
    App.Matrix(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1)
)

TEMPLATE_FILTER = "Pbrt templates (pbrt_*.pbrt)"

# ===========================================================================
#                             Write functions
# ===========================================================================


def write_mesh(name, mesh, material, vertex_normals=False):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""
    matval = material.get_material_values(
        name, _write_texture, _write_value, _write_texref
    )
    material = _write_material(name, matval)
    pnts = [f"{p[0]:+18.8f} {p[1]:+18.8f} {p[2]:+18.8f}" for p in mesh.Points]
    ind_precision = math.ceil(math.log10(len(pnts)))
    pnts = _format_list(pnts, 2)
    inds = [
        f"{i[0]:{ind_precision}} {i[1]:{ind_precision}} {i[2]:{ind_precision}}"
        for i in mesh.Facets
    ]
    inds = _format_list(inds, 5)
    if mesh.has_uvmap():
        if matval.has_textures():
            # Here we transform uv according to texture transformation
            # This is necessary as pbrt texture transformation features are
            # incomplete. They lack rotation in general, and full
            # transformation for normal map.
            tex = next(iter(matval.texobjects.values()))  # Take 1st texture
            translate = -App.Base.Vector2d(
                tex.translation_u, tex.translation_v
            )
            rotate = -tex.rotation
            scale = 1.0 / tex.scale if tex.scale != 0.0 else 1.0
            uvbase = mesh.transformed_uvmap(translate, rotate, scale)
        else:
            uvbase = mesh.uvmap
        uvs = [f"{t[0]:+18.8f} {t[1]:+18.8f}" for t in uvbase]
        uvs = _format_list(uvs, 3)
        uvs = f"""    "point2 uv" [\n{uvs}\n    ]\n"""
    else:
        uvs = ""

    if vertex_normals:
        nrms = [
            f"{v.x:+18.8f} {v.y:+18.8f} {v.z:+18.8f}"
            for v in mesh.getPointNormals()
        ]
        nrms = _format_list(nrms, 2)
        normals = f"""\
    "normal N" [
{nrms}
    ]
"""
    else:
        normals = ""

    snippet = f"""# Object '{name}'
AttributeBegin

{matval.write_textures()}
{material}
  Shape "trianglemesh"
    "point3 P" [
{pnts}
    ]
    "integer indices" [
{inds}
    ]
{normals}
{uvs}
AttributeEnd
# ~Object '{name}'
"""
    return snippet


def write_camera(name, pos, updir, target, fov, resolution, **kwargs):
    """Compute a string in renderer SDL to represent a camera."""
    snippet = """# Camera '{n}'
Scale -1 1 1
LookAt {p.x:+18.8f} {p.y:+18.8f} {p.z:+18.8f}
       {t.x:+18.8f} {t.y:+18.8f} {t.z:+18.8f}
       {u.x:+18.8f} {u.y:+18.8f} {u.z:+18.8f}
Camera "perspective" "float fov" {f:+.5f}
# ~Camera '{n}'"""  # NB: do not modify enclosing comments in snippet
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
    points = [f"{p.x:+18.6} {p.y:+18.6} {p.z:+18.6}" for p in points]
    points = _format_list(points, 2)

    power *= 100

    snippet = """# Arealight '{n}'
AttributeBegin
  AreaLightSource "diffuse"
    "rgb L" [{c[0]} {c[1]} {c[2]}]
    "bool twosided" true
    "float scale" [{s}]
  Shape "trianglemesh"
    "integer indices" [0 1 2  0 2 3]
    "point3 P" [
{p}
    ]
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
    "rgb L" [0.18 0.28 0.75]
    "float scale" 1.5
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
    snippet = [
        f"  # Material '{name}'",
        r'  Material "dielectric"',
        f'    {matval["ior"]}',
    ]
    _write_bump_and_normal(snippet, matval)

    return "\n".join(snippet)


def _write_material_disney(name, matval):
    """Compute a string in the renderer SDL for a Disney material."""
    # Disney is no more supported in pbrt v4 (in contrast to pbrt v3), so this
    # function will not compute anything...
    # pylint: disable=unused-argument
    return ""


def _write_material_diffuse(name, matval):
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet = [
        f"  # Material '{name}'",
        r'  Material "diffuse"',
        f'    {matval["color"]}',
    ]
    _write_bump_and_normal(snippet, matval)

    return "\n".join(snippet)


def _write_material_pbr(name, matval):
    """Compute a string in the renderer SDL for a PBR material."""
    bump_snippet = f"""{matval["bump"]}""" if matval.has_bump() else ""
    normal_snippet = f"""{matval["normal"]}""" if matval.has_normal() else ""
    roughness = matval["roughness"]

    snippet = f"""\
  # Material '{name}'
  MakeNamedMaterial "{name}_diffuse"
    "string type" "diffuse"
    {matval["basecolor"]}
    # {roughness}
    {bump_snippet}
    {normal_snippet}
  MakeNamedMaterial "{name}_metallic"
    "string type" "conductor"
    {matval["basecolor"]}
    {roughness}
    {bump_snippet}
    {normal_snippet}
  Material "mix"
    "string materials" ["{name}_diffuse" "{name}_metallic"]
    {matval["metallic"]}
  # ~Material '{name}'
"""

    return snippet


def _write_bump_and_normal(snippet, matval):
    """Write bump and normal sub-snippets to snippet (helper)."""
    if matval.has_bump():
        snippet.append(f"""    {matval["bump"]}""")
    if matval.has_normal():
        snippet.append(f"""    {matval["normal"]}""")
    snippet.append("")


def _write_material_mixed(name, matval):
    """Compute a string in the renderer SDL for a Mixed material."""
    # Bump
    bump_snippet = f"""{matval["bump"]}""" if matval.has_bump() else ""

    # Glass
    submat_g = matval.getmixedsubmat("glass", name + "_glass")
    snippet_g_tex = submat_g.write_textures()

    # Diffuse
    submat_d = matval.getmixedsubmat("diffuse", name + "_diffuse")
    snippet_d_tex = submat_d.write_textures()

    snippet = f"""  # Material '{name}'
{snippet_d_tex}
  MakeNamedMaterial "{name}_diffuse"
    "string type" "diffuse"
{submat_d["color"]}
{bump_snippet}
{snippet_g_tex}
  MakeNamedMaterial "{name}_glass"
    "string type" "dielectric"
{submat_g["ior"]}
{bump_snippet}
  Material "mix"
    "string materials" ["{name}_diffuse" "{name}_glass"]
{matval["transparency"]}"""
    return snippet


def _write_material_carpaint(name, matval):
    """Compute a string in the renderer SDL for a carpaint material."""
    # Bump
    bump_snippet = f"""{matval["bump"]}""" if matval.has_bump() else ""

    snippet = f"""  # Material '{name}'
  Material "coateddiffuse"
{matval["basecolor"]}
    "float roughness" [ 0.0 ]
    "float eta" [ 1.54 ]
{bump_snippet}"""
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
    "Substance_PBR": _write_material_pbr,
}


# ===========================================================================
#                            Texture management
# ===========================================================================


def _texname(**kwargs):
    """Compute texture name (helper).

    For a texture name common to _write_texture and _write_texref.
    """
    objname = kwargs["objname"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    return f"{objname}_{shadertype}_{propname}_tex"


def _write_texture(**kwargs):
    """Compute a string in renderer SDL to describe a texture.

    Returns:
        the name of the texture
        the SDL string of the texture
    """
    # Retrieve parameters
    propname = kwargs["propname"]
    proptype = kwargs["proptype"]
    propvalue = kwargs["propvalue"]

    texname = _texname(**kwargs)

    # Exclusion
    if propname == "normal":
        return texname, ""
    if propname == "displacement":
        return texname, ""

    # Special cases
    if propname == "bump":
        texname2 = texname
        texname = texname + "_unscaled"

    # Compute texture parameters
    textype, encoding = (
        ("spectrum", "sRGB") if proptype == "RGB" else ("float", "linear")
    )
    filebasename = os.path.basename(propvalue.file)

    # Compute snippet (transformation is in uv...)
    snippet = f"""  Texture "{texname}" "{textype}" "imagemap"
    "string filename" "{filebasename}"
    "string mapping" "uv"
    "string encoding" "{encoding}"
"""

    # Bump scale
    if propname == "bump":
        snippet += f"""  Texture "{texname2}" "float" "scale"
    "texture tex" "{texname}"
    "float scale" 2.0
"""

    return texname, snippet


_VALSNIPPETS = {
    "RGB": '"rgb {field}" [{val.r:.8} {val.g:.8} {val.b:.8}]',
    "float": '"float {field}" {val:.8}',
    "node": "",
    "texonly": "{val}",
    "str": "{val}",
}

_FIELD_MAPPING = {
    ("Diffuse", "color"): "reflectance",
    ("Diffuse", "bump"): "displacement",
    ("Glass", "ior"): "eta",
    ("Glass", "bump"): "displacement",
    ("Carpaint", "basecolor"): "reflectance",
    ("Carpaint", "bump"): "displacement",
    ("diffuse", "color"): "reflectance",
    ("glass", "ior"): "eta",
    ("Mixed", "transparency"): "amount",
    ("Mixed", "bump"): "displacement",
    ("Substance_PBR", "basecolor"): "reflectance",
    ("Substance_PBR", "metallic"): "amount",
    ("Substance_PBR", "bump"): "displacement",
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
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    propvalue = kwargs["propvalue"]

    # Field name
    field = _FIELD_MAPPING.get((shadertype, propname), propname)

    # Exclusions / special cases
    if propname == "ior":
        msg = (
            "[Render][Pbrt] WARNING - pbrt does not support texture for "
            "ior. Falling back to default constant value (1.5)\n"
        )
        App.Console.PrintWarning(msg)
        return ""
    if propname == "displacement":
        msg = "[Render][Pbrt] WARNING - pbrt does not support displacement.\n"
        App.Console.PrintWarning(msg)
        return ""
    if propname == "normal":
        basefilename = os.path.basename(propvalue.file)
        snippet = f'''"string normalmap" "{basefilename}"'''
        if (
            propvalue.scale != 1.0
            or propvalue.translation_u != 0.0
            or propvalue.translation_v != 0.0
        ):
            msg = (
                "[Render][Pbrt] WARNING - pbrt does not support scaling or "
                "translation for normal map.\n"
            )
            App.Console.PrintWarning(msg)
        return snippet

    # Texture name
    texname = _texname(**kwargs)

    # Snippet for texref
    snippet = f'''"texture {field}" "{texname}"'''

    return snippet


# ===========================================================================
#                              Helpers
# ===========================================================================


def _format_list(inlist, elements_per_line, indentation=6):
    """Format list of numbers, to improve readability."""
    elements_per_line = int(elements_per_line)
    pad = " " * int(indentation)

    # Group by 'elements_per_line'
    res = itertools.groupby(
        enumerate(inlist), lambda x: int(x[0]) // int(elements_per_line)
    )
    res = [pad.join([i for _, i in sublist]) for _, sublist in res]

    # Indent
    res = [textwrap.indent(i, pad) for i in res]
    res = "\n".join(res)
    return res


# ===========================================================================
#                              Render function
# ===========================================================================


def render(
    project, prefix, batch, input_file, output_file, width, height, spp, denoise
):
    """Generate renderer command.

    Args:
        project -- The project to render
        prefix -- A prefix string for call (will be inserted before path to
            renderer)
        batch -- A boolean indicating whether to call UI (False) or console
            (True) version of renderer.
        input_file -- path to input file
        output -- path to output file
        width -- Rendered image width, in pixels
        height -- Rendered image height, in pixels
        spp -- Max samples per pixel (halt condition)
        denoise -- Flag to run denoiser

    Returns:
        The command to run renderer (string)
        A path to output image file (string)
    """
    # Make various adjustments on file:
    # Reorder camera declarations and set width/height
    with open(input_file, "r", encoding="utf-8") as f:
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
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(template)

    # Denoiser (ignored)
    if denoise:
        wrn = (
            "[Render][Pbrt] WARNING - Denoiser flag will be ignored: "
            "Pbrt has no denoising capabilities.\n"
        )
        App.Console.PrintWarning(wrn)

    # Build command and launch
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    prefix = params.GetString("Prefix", "")
    if prefix:
        prefix += " "
    rpath = params.GetString("PbrtPath", "")
    args = params.GetString("PbrtParameters", "")
    if not batch:
        # Caveat: pbrt does not really provide a GUI interactive mode;
        # instead it is capable to send intermediate frames to 'tev', an
        # exr viewer (https://github.com/Tom94/tev)
        # Open a tev session, set batch to False, run pbrt and you'll be able
        # to visualize progressive rendering.
        args += "--display-server localhost:14158 "  # For tev...
    args += f' --outfile "{output_file}" '
    if spp:
        args += f" --spp {spp} "
    if not rpath:
        App.Console.PrintError(
            "Unable to locate renderer executable. "
            "Please set the correct path in "
            "Edit -> Preferences -> Render\n"
        )
        return None, None

    filepath = f'"{input_file}"'

    cmd = prefix + rpath + " " + args + " " + filepath

    return cmd, output_file
