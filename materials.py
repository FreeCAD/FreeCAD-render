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
#                           Module imports
# ===========================================================================


import collections
import types
import ast


# ===========================================================================
#                        rendering_material construction
# ===========================================================================

RGB = collections.namedtuple("RGB", "r g b")
RGBA = collections.namedtuple("RGB", "r g b a")


# TODO Document expected material card syntax in README
def get_rendering_material(material, renderer, default_color):
    # TODO Update docstring
    # TODO Add log instructions (to help debug)
    """This function implements rendering material logic.

    It extracts a data class of rendering parameters from a FreeCAD material
    card.
    The workflow is the following:
    - If the material card contains a renderer-specific passthrough field, the
    dictionary is built with those parameters
    - Otherwise, if the material card contains Disney-principled shader
    parameters, the dictionary is built with those parameters
    - Otherwise, if the material card contains a Graphic section, the
    dictionary contains the related parameters (Diffuse, Transparency). This
    is a backward compatibility fallback
    - Otherwise, if the material card contains a valid 'father' field, the
    above process is applied to the father card
    - Otherwise, a white matte material is returned

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

    def str2rgb(string):
        """Convert a ({r},{g},{b})-like string into RGB object"""
        float_tuple = map(float, ast.literal_eval(string))
        return RGB._make(float_tuple)

    mat = dict(material)
    renderer = str(renderer)

    res = types.SimpleNamespace()  # Result

    # TODO Add a level of object for specific parameters

    # Try renderer Passthrough
    try:
        string = str(mat["Render.{}.Passthrough".format(renderer)])
    except KeyError:
        pass
    else:
        res.passthrough = types.SimpleNamespace()
        res.passthrough.string = string
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
        # TODO Issue a warning if one of the Disney parameters is present
        # without any BaseColor ?
        pass
    else:
        res.disney = types.SimpleNamespace()
        res.disney.basecolor = basecolor
        res.disney.subsurface = float(mat.get("Render.Disney.Subsurface", "0"))
        res.disney.metallic = float(mat.get("Render.Disney.Metallic", "0"))
        res.disney.specular = float(mat.get("Render.Disney.Specular", "0"))
        res.disney.speculartint = \
            float(mat.get("Render.Disney.SpecularTint", "0"))
        res.disney.roughness = float(mat.get("Render.Disney.Roughness", "0"))
        res.disney.anisotropic = \
            float(mat.get("Render.Disney.Anisotropic", "0"))
        res.disney.sheen = float(mat.get("Render.Disney.Sheen", "0"))
        res.disney.sheentint = float(mat.get("Render.Disney.SheenTint", "0"))
        res.disney.clearcoat = float(mat.get("Render.Disney.ClearCoat", "0"))
        res.disney.clearcoatgloss = \
            float(mat.get("Render.Disney.ClearCoatGloss", "0"))
        res.shadertype = "Disney"
        res.color = RGBA(*basecolor, 1.0)
        return res

    # Try with Coin-like parameters
    try:
        diffusecolor = str2rgb(mat["DiffuseColor"])
    except KeyError:
        pass
    else:
        res.diffuse = types.SimpleNamespace()
        res.diffuse.color = diffusecolor
        res.diffuse.alpha = 1.0 - float(mat.get("Transparency"), "0")
        res.shadertype = "Diffuse"
        res.color = RGBA(*diffusecolor, res.diffuse.alpha)
        return res

    # TODO Escalation to Father

    # Default color
    try:
        diffusecolor = RGB(*default_color[:3])
        diffusealpha = default_color[3]
    except IndexError:
        diffusecolor = RGB(1.0, 1.0, 1.0)
        diffusealpha = 1.0
    else:
        res.diffuse = types.SimpleNamespace()
        res.diffuse.color = diffusecolor
        res.diffuse.alpha = diffusealpha
        res.shadertype = "Diffuse"
        res.color = RGBA(*diffusecolor, diffusealpha)
        return res
