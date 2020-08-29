# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements material management mechanisms for rendering"""

# ===========================================================================
#                           Imports
# ===========================================================================


import collections
import types
import functools

import FreeCAD as App

from renderutils import RGB, RGBA, str2rgb, debug as ru_debug


# ===========================================================================
#                                   Export
# ===========================================================================

Param = collections.namedtuple("Param", "name type default desc")

STD_MATERIALS_PARAMETERS = {
    "Glass": [
        Param("IOR", "float", 1.5, "Index of refraction"),
        Param("Color", "RGB", (1, 1, 1), "Transmitted color")],

    "Disney": [
        Param("BaseColor", "RGB", (0.8, 0.8, 0.8), "Base color"),
        Param("Subsurface", "float", 0.0, "Subsurface coefficient"),
        Param("Metallic", "float", 0.0, "Metallic coefficient"),
        Param("Specular", "float", 0.0, "Specular coefficient"),
        Param("SpecularTint", "float", 0.0, "Specular tint coefficient"),
        Param("Roughness", "float", 0.0, "Roughness coefficient"),
        Param("Anisotropic", "float", 0.0, "Anisotropic coefficient"),
        Param("Sheen", "float", 0.0, "Sheen coefficient"),
        Param("SheenTint", "float", 0.0, "Sheen tint coefficient"),
        Param("ClearCoat", "float", 0.0, "Clear coat coefficient"),
        Param("ClearCoatGloss", "float", 0.0, "Clear coat gloss coefficient")],

    "Diffuse": [
        Param("Color", "RGB", (0.8, 0.8, 0.8), "Diffuse color")],

    }


STD_MATERIALS = sorted(list(STD_MATERIALS_PARAMETERS.keys()))

CAST_FUNCTIONS = {"float": float, "RGB": str2rgb, "string": str}


# TODO Use a cache, do not recompute each time
def get_rendering_material(material, renderer, default_color):
    """This function implements rendering material logic.

    It extracts a data class of rendering parameters from a FreeCAD material
    card.
    The workflow is the following:
    - If the material card contains a renderer-specific Passthrough field, the
      dictionary is built with those parameters
    - Otherwise, if the material card contains standard materials parameters,
      the dictionary is built with those parameters
    - Otherwise, if the material card contains a valid 'father' field, the
      above process is applied to the father card
    - Otherwise, if the material card contains a Graphic section
      (diffusecolor), a Diffuse material is built and the dictionary contains
      the related parameters . This is a backward compatibility fallback
    - Otherwise, a Diffuse material made with default_color is returned

    Parameters:
    material -- a FreeCAD material
    renderer -- the targeted renderer (string, case sensitive)
    default_color -- a RGBA color, to be used as a fallback

    Returns:
    A data object providing some systematic and specific properties for the
    targeted shader.

    Systematic properties:
    shadertype -- the type of shader for rendering. Can be "Passthrough",
    "Disney", "Glass", "Diffuse"

    Specific properties, depending on 'shadertype':
    "Passthrough": string, renderer
    "Disney": basecolor, subsurface, metallic, specular, speculartint,
    roughness, anisotropic, sheen, sheentint, clearcoat, clearcoatgloss
    "Glass": ior, color
    "Diffuse": color

    Please note the function is not responsible for syntactic compliance of the
    parameters in the material card (i.e. the parameters are not parsed, just
    collected from the material card)
    """
    # TODO Test if Material is valid (to avoid unnecessary treatments)

    # Initialize
    try:
        mat = dict(material.Material)
    except (KeyError, AttributeError):
        name = "<Unnamed Material>"
        mat = dict()

    renderer = str(renderer)
    name = mat.get("Name", "<Unnamed Material>")
    debug = functools.partial(ru_debug, "Material", name)

    debug("Starting material computation")

    res = types.SimpleNamespace()  # Result

    # Try renderer Passthrough
    common_keys = passthrough_keys(renderer) & mat.keys()
    if common_keys:
        debug("Found valid Passthrough - returning")
        lines = [mat[k] for k in sorted(common_keys)]
        res.shadertype = "Passthrough"
        res.passthrough = types.SimpleNamespace()
        res.passthrough.string = "\n".join(lines)
        res.passthrough.renderer = renderer
        res.default_color = default_color
        return res

    # Try standard materials
    try:
        shadertype = str(mat["Render.Type"])
        assert shadertype in STD_MATERIALS_PARAMETERS
    except KeyError:
        pass
    except AssertionError:
        debug("Unknown material type '{}'".format(shadertype))
    else:
        debug("Found valid {} - returning".format(shadertype))
        setattr(res, "shadertype", shadertype)
        subobj = types.SimpleNamespace()
        setattr(res, shadertype.lower(), subobj)
        for par in STD_MATERIALS_PARAMETERS[shadertype]:
            key = "Render.{}.{}".format(shadertype, par.name)
            cast_function = CAST_FUNCTIONS[par.type]
            try:
                value = cast_function(mat[key])
            except (KeyError, TypeError):
                value = cast_function(par.default)
            finally:
                setattr(subobj, par.name.lower(), value)
        res.default_color = get_default_color(res)
        return res

    # Climb up to Father
    debug("No valid material definition - trying father material")
    try:
        father_name = mat["Father"]
        assert father_name
    except (KeyError, AssertionError):
        # No father
        debug("No valid father")
    else:
        # Retrieve all valid materials
        materials = (o for o in App.ActiveDocument.Objects
                     if is_valid_material(o))
        # Find father material
        try:
            father = next(m for m in materials
                          if m.Material.get("Name", "") == father_name)
        except StopIteration:
            msg = "Found father material name ('{}') but "\
                  "did not find this material in active document"
            debug(msg.format(father_name))
        else:
            debug("Retrieve father material '{}'".format(father_name))
            return get_rendering_material(father, renderer, default_color)

    # Try with Coin-like parameters (backward compatibility)
    try:
        diffusecolor = str2rgb(mat["DiffuseColor"])
    except KeyError:
        pass
    else:
        debug("Fallback to Coin-like parameters")
        return _build_diffuse(diffusecolor,
                              1.0 - float(mat.get("Transparency", "0")))

    # Default color
    try:
        diffusecolor = RGB(*default_color[:3])
        diffusealpha = default_color[3]
    except IndexError:
        diffusecolor = RGB(0.8, 0.8, 0.8)
        diffusealpha = 1.0
    else:
        debug("Fallback to default color")
        return _build_diffuse(diffusecolor, diffusealpha)


def passthrough_keys(renderer):
    """Return material card keys for passthrough rendering material"""
    return {"Render.{}.{:04}".format(renderer, i) for i in range(1, 9999)}


def is_multimat(obj):
    """Check if a material is a multimaterial."""
    return (obj is not None and
            obj.isDerivedFrom("App::FeaturePython") and
            obj.Proxy.Type == "MultiMaterial")


def get_default_color(material):
    """Provide a default color for a material (as a fallback)."""
    shadertype = getattr(material, "shadertype", "")
    if shadertype == "Diffuse":
        color = material.diffuse.color
    elif shadertype == "Disney":
        color = material.disney.basecolor
    elif shadertype == "Glass":
        color = material.glass.color
    else:
        color = RGB(0.8, 0.8, 0.8)
    return color


def generate_param_doc():
    """Generate documentation for material rendering parameters.

    The documentation is generated in Markdown format.
    """
    header_fmt = ["#### **{m}** Material",
                  "",
                  "`Render.Type={m}`",
                  "",
                  "Parameter | Type | Default value | Description",
                  "--------- | ---- | ------------- | -----------"]

    line_fmt = "`Render.{m}.{p.name}` | {p.type} | {p.default} | {p.desc}"
    footer_fmt = [""]
    lines = []
    for mat in STD_MATERIALS:
        lines += [l.format(m=mat) for l in header_fmt]
        lines += [line_fmt.format(m=mat, p=param)
                  for param in STD_MATERIALS_PARAMETERS[mat]]
        lines += footer_fmt

    return '\n'.join(lines)


# ===========================================================================
#                            Locals (helpers)
# ===========================================================================


def _build_diffuse(diffusecolor, alpha=1.0):
    """Build diffuse material from a simple RGB color"""
    res = types.SimpleNamespace()
    res.diffuse = types.SimpleNamespace()
    res.diffuse.color = diffusecolor
    res.diffuse.alpha = alpha
    res.shadertype = "Diffuse"
    res.color = RGBA(*diffusecolor, res.diffuse.alpha)
    res.default_color = diffusecolor
    return res


def _get_float(material, param_prefix, param_name, default=0.0):
    """Get float value in material dictionary"""
    return material.get(param_prefix + param_name, default)


def is_valid_material(obj):
    """Assert that an object is a valid Material"""
    return (obj.isDerivedFrom("App::MaterialObjectPython")
            and hasattr(obj, "Material")
            and isinstance(obj.Material, dict))
