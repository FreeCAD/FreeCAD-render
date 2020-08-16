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
# TODO Feature to add a Material property (App::PropertyLink) to a shape

# ===========================================================================
#                           Imports
# ===========================================================================


import collections
import types
import ast
import functools

import FreeCAD as App

from renderutils import RGB, str2rgb, debug as ru_debug


# ===========================================================================
#                                   Export
# ===========================================================================

# TODO Document expected material card syntax in README
# TODO Use a cache, do not recompute each time
def get_rendering_material(material, renderer, default_color):
    """This function implements rendering material logic.

    It extracts a data class of rendering parameters from a FreeCAD material
    card.
    The workflow is the following:
    - If the material card contains a renderer-specific Passthrough field, the
    dictionary is built with those parameters
    - Otherwise, if the material card contains a Glass shader set of
    parameters, the dictionary is built with those parameters
    - Otherwise, if the material card contains a Diffuse shader set of
    parameters, the dictionary is built with those parameters
    - Otherwise, if the material card contains Disney-principled shader
    parameters, the dictionary is built with those parameters
    - Otherwise, if the material card contains a valid 'father' field, the
    above process is applied to the father card
    - Otherwise, if the material card contains a Graphic section
    (diffusecolor), a Diffuse material is built and the dictionary contains
    the related parameters . This is a backward compatibility fallback
    - Otherwise, a Diffuse material made with default_color is returned

    Parameters:
    material -- a FreeCAD material, as a dictionary of properties/values
    renderer -- the targeted renderer (string, case sensitive)
    default_color -- a RGBA color, to be used as a fallback

    Returns:
    A data object providing some systematic and specific properties for the
    targeted shader.

    Systematic properties:
    shadertype -- the type of shader for rendering. Can be "Passthrough",
    "Disney", "Glass", "Diffuse"
    color -- the base color (RGBA) of the material - to be used as a fallback
    by the renderer if it cannot interpret the shader

    Specific properties, depending on 'shadertype', in gathered in subobjects:
    "Passthrough": string, renderer
    "Disney": basecolor, subsurface, metallic, specular, speculartint,
    roughness, anisotropic, sheen, sheentint, clearcoat, clearcoatgloss
    "Glass": ior, color
    "Diffuse": color, alpha


    Please note the function is not responsible for syntactic compliance of the
    parameters in the material card (i.e. the parameters are not parsed, just
    collected from the material card)
    """


    # TODO Test if Material is None (to avoid unnecessary treatments)
    # get_rendering_material starts here

    try:
        mat = dict(material.Material)
    except Exception:
        name = "<Unnamed Material>"
        mat = dict()

    renderer = str(renderer)
    name = mat.get("Name", "<Unnamed Material>")
    debug = functools.partial(ru_debug, "Material", name)

    debug("Starting material computation")

    res = types.SimpleNamespace()  # Result

    # Try renderer Passthrough
    try:
        lines = [mat["Render.{}.0001".format(renderer)]]
    except KeyError:
        pass
    else:
        debug("Found valid Passthrough - returning")
        passthru_keys = ["Render.{}.{:04}".format(renderer, i)
                         for i in range(2, 9999)]
        lines += [mat[k] for k in passthru_keys if k in mat.keys()]
        res.passthrough = types.SimpleNamespace()
        res.passthrough.string = "\n".join(lines)
        res.passthrough.renderer = renderer
        res.shadertype = "Passthrough"
        res.color = default_color
        return res

    # Try Glass
    # We require an IOR. Other parameters are optional
    try:
        ior = float(mat["Render.Glass.IOR"])
    except KeyError:
        pass
    else:
        debug("Found valid Glass - returning")
        res.glass = types.SimpleNamespace()
        res.glass.ior = ior
        res.glass.color = str2rgb(mat.get("Render.Glass.Color", "(1,1,1)"))
        res.shadertype = "Glass"
        res.color = RGBA(*res.glass.color, 0.5)
        return res

    # Try Disney material
    # We require a base color. Other parameters optional
    # https://disney-animation.s3.amazonaws.com/library/s2012_pbs_disney_brdf_notes_v2.pdf
    try:
        basecolor = str2rgb(mat["Render.Disney.BaseColor"])
    except KeyError:
        pass
    else:
        debug("Found valid Disney - returning")
        res.disney = types.SimpleNamespace()
        res.disney.basecolor = basecolor
        prefix = "Render.Disney."
        getf = functools.partial(_get_float, mat, prefix)
        res.disney.subsurface = getf("Subsurface")
        res.disney.metallic = getf("Metallic")
        res.disney.specular = getf("Specular")
        res.disney.speculartint = getf("SpecularTint")
        res.disney.roughness = getf("Roughness")
        res.disney.anisotropic = getf("Anisotropic")
        res.disney.sheen = getf("Sheen")
        res.disney.sheentint = getf("SheenTint")
        res.disney.clearcoat = getf("ClearCoat")
        res.disney.clearcoatgloss = getf("ClearCoatGloss")

        res.shadertype = "Disney"
        res.color = RGBA(*basecolor, 1.0)
        return res

    # Try Diffuse
    try:
        diffusecolor = str2rgb(mat["Render.Diffuse.Color"])
    except KeyError:
        pass
    else:
        debug("Found valid Diffuse - returning")
        return _build_diffuse(diffusecolor)

    # Escalation to Father
    debug("No valid material definition - trying father material")
    try:
        father_name = mat["Father"]
        assert father_name
    except (KeyError, AssertionError):
        # No father
        debug("No valid father")
    else:
        # Retrieve all valid materials
        materials = (o.Material for o in App.ActiveDocument.Objects
                     if o.isDerivedFrom("App::MaterialObjectPython") and
                     hasattr(o, "Material") and
                     isinstance(o.Material, dict))
        # Find father material
        try:
            father = next(m for m in materials
                          if m.get("Name", "") == father_name)
        except StopIteration:
            msg = "Found father material name ('{}') but "\
                  "did not find this material in active document"
            debug(msg.format(father_name))
        else:
            debug("Escalate to father material '{}'".format(father_name))
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
        # TODO Default should not be pure white
        diffusecolor = RGB(1.0, 1.0, 1.0)
        diffusealpha = 1.0
    else:
        debug("Fallback to default color")
        return _build_diffuse(diffusecolor, diffusealpha)


def is_multimat(obj):
    """Check if a material is a multimaterial"""
    return (obj is not None and
            obj.isDerivedFrom("App::FeaturePython") and
            obj.Proxy.Type == "MultiMaterial")


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
    return res


def _get_float(material, param_prefix, param_name, default=0.0):
    """Get float value in material dictionary"""
    return material.get(param_prefix + param_name, default)
