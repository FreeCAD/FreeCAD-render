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

"""This module implements material management mechanisms for rendering."""

# ===========================================================================
#                           Imports
# ===========================================================================


import collections
import types
import functools

import FreeCAD as App

from renderutils import RGB, RGBA, str2rgb, debug as ru_debug, getproxyattr


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

    "Mixed": [
        Param("Glass.IOR", "float", 1.5, "Index of refraction"),
        Param("Glass.Color", "RGB", (1, 1, 1), "Transmitted color"),
        Param("Diffuse.Color", "RGB", (0.8, 0.8, 0.8), "Diffuse color"),
        Param("Ratio", "float", 0.5, "Mix ratio glass vs diffuse (in [0,1])")],
    }


STD_MATERIALS = sorted(list(STD_MATERIALS_PARAMETERS.keys()))

CAST_FUNCTIONS = {"float": float, "RGB": str2rgb, "string": str}


def get_rendering_material(material, renderer, default_color):
    """Get rendering material from FreeCAD material.

    This function implements rendering material logic.
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
    # Check valid material
    if not is_valid_material(material):
        ru_debug("Material", "<None>", "Fallback to default material")
        return _build_fallback(default_color)

    # Initialize
    mat = dict(material.Material)
    renderer = str(renderer)
    name = mat.get("Name", "<Unnamed Material>")
    debug = functools.partial(ru_debug, "Material", name)

    debug("Starting material computation")

    # Try renderer Passthrough
    common_keys = passthrough_keys(renderer) & mat.keys()
    if common_keys:
        lines = tuple(mat[k] for k in sorted(common_keys))
        debug("Found valid Passthrough - returning")
        return _build_passthrough(lines, renderer, default_color)

    # Try standard materials
    shadertype = mat.get("Render.Type", None)
    if shadertype:
        try:
            params = STD_MATERIALS_PARAMETERS[shadertype]
        except KeyError:
            debug("Unknown material type '{}'".format(shadertype))
        else:
            keyfmt = "Render.%s.%s"
            values = tuple((p.name,
                            mat.get(keyfmt % (shadertype, p.name), None),
                            p.default,
                            p.type)
                           for p in params)
            return _build_standard(shadertype, values)

    # Climb up to Father
    debug("No valid material definition - trying father material")
    try:
        father_name = mat["Father"]
        assert father_name
        materials = (o for o in App.ActiveDocument.Objects
                     if is_valid_material(o))
        father = next(m for m in materials
                      if m.Material.get("Name", "") == father_name)
    except (KeyError, AssertionError):
        # No father
        debug("No valid father")
    except StopIteration:
        # Found father, but not in document
        msg = "Found father material name ('{}') but "\
              "did not find this material in active document"
        debug(msg.format(father_name))
    else:
        # Found usable father
        debug("Retrieve father material '{}'".format(father_name))
        return get_rendering_material(father, renderer, default_color)

    # Try with Coin-like parameters (backward compatibility)
    try:
        diffusecolor = str2rgb(mat["DiffuseColor"])
    except (KeyError, TypeError):
        pass
    else:
        debug("Fallback to Coin-like parameters")
        color = RGBA(diffusecolor.r,
                     diffusecolor.g,
                     diffusecolor.b,
                     float(mat.get("Transparency", "0")) / 100)
        return _build_fallback(color)

    # Fallback with default_color
    debug("Fallback to default color")
    return _build_fallback(default_color)


@functools.lru_cache(maxsize=128)
def passthrough_keys(renderer):
    """Compute material card keys for passthrough rendering material."""
    return {"Render.{}.{:04}".format(renderer, i) for i in range(1, 9999)}


def is_multimat(obj):
    """Check if a material is a multimaterial."""
    try:
        is_app_feature = obj.isDerivedFrom("App::FeaturePython")
    except AttributeError:
        return False

    is_type_multimat = getproxyattr(obj, "Type", None) == "MultiMaterial"

    return obj is not None and is_app_feature and is_type_multimat


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
    """Generate Markdown documentation from material rendering parameters."""
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
        lines += [h.format(m=mat) for h in header_fmt]
        lines += [line_fmt.format(m=mat, p=param)
                  for param in STD_MATERIALS_PARAMETERS[mat]]
        lines += footer_fmt

    return '\n'.join(lines)


def is_valid_material(obj):
    """Assert that an object is a valid Material."""
    try:
        is_materialobject = obj.isDerivedFrom("App::MaterialObjectPython")
    except AttributeError:
        return False

    return (obj is not None
            and is_materialobject
            and hasattr(obj, "Material")
            and isinstance(obj.Material, dict))


# ===========================================================================
#                            Locals (helpers)
# ===========================================================================


class RenderMaterial:
    """An object to represent a material for renderers plugins."""

    def __init__(self, shadertype):
        """Initialize object."""
        shadertype = str(shadertype)
        self.shadertype = shadertype
        setattr(self, shadertype.lower(), types.SimpleNamespace())
        self.default_color = RGBA(0.8, 0.8, 0.8, 1.0)

    def __repr__(self):
        """Represent object."""
        items = (f"{k}={v!r}" for k, v in self.__dict__.items())
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def setshaderparam(self, name, value):
        """Set shader parameter.

        If parameter does not exist, add it.
        If parameter name is a compound like 'foo.bar.baz', foo and bar are
        added as SimpleNamespaces.
        """
        path = [e.lower() for e in [self.shadertype] + name.split('.')]
        res = self
        for elem in path[:-1]:
            if not hasattr(res, elem):
                setattr(res, elem, types.SimpleNamespace())
            res = getattr(res, elem)
        setattr(res, path[-1], value)

    @property
    def shader(self):
        """Get shader attribute, whatever underlying attribute it is."""
        return getattr(self, self.shadertype.lower())



@functools.lru_cache(maxsize=128)
def _build_diffuse(diffusecolor, alpha=1.0):
    """Build diffuse material from a simple RGB color."""
    res = RenderMaterial("Diffuse")
    res.shader.color = diffusecolor
    res.shader.alpha = alpha
    res.default_color = diffusecolor
    return res


@functools.lru_cache(maxsize=128)
def _build_standard(shadertype, values):
    """Build standard material."""
    res = RenderMaterial(shadertype)

    for nam, val, dft, typ in values:
        cast_function = CAST_FUNCTIONS[typ]
        try:
            value = cast_function(val)
        except TypeError:
            value = cast_function(dft)
        res.setshaderparam(nam, value)

    res.default_color = get_default_color(res)  # TODO Put it in parameters
    return res


@functools.lru_cache(maxsize=128)
def _build_passthrough(lines, renderer, default_color):
    """Build passthrough material."""
    res = RenderMaterial("Passthrough")
    res.shader.string = _convert_passthru("\n".join(lines))
    res.shader.renderer = renderer
    res.default_color = default_color
    return res


@functools.lru_cache(maxsize=128)
def _build_fallback(color):
    """Build fallback material (mixed).

    color -- a RGBA tuple color
    """
    try:
        _color = ','.join([str(c) for c in color[:3]])
        _alpha = str(color[3])
    except IndexError:
        _color = "0.8, 0.8, 0.8"
        _alpha = "0.0"

    values = (("Glass.IOR", "1.5", "1.5", "float"),
              ("Glass.Color", _color, _color, "RGB"),
              ("Diffuse.Color", _color, _color, "RGB"),
              ("Ratio", _alpha, _alpha, "float"))

    return _build_standard("Mixed", values)


def _get_float(material, param_prefix, param_name, default=0.0):
    """Get float value in material dictionary."""
    return material.get(param_prefix + param_name, default)


PASSTHRU_REPLACED_TOKENS = (("{", "{{"),
                            ("}", "}}"),
                            ("%NAME%", "{n}"),
                            ("%RED%", "{c.r}"),
                            ("%GREEN%", "{c.g}"),
                            ("%BLUE%", "{c.b}"))


@functools.lru_cache(maxsize=128)
def _convert_passthru(passthru):
    """Convert a passthrough string from FCMat format to Python FSML.

    (FSML stands for Format Specification Mini-Language)
    """
    for token in PASSTHRU_REPLACED_TOKENS:
        passthru = passthru.replace(*token)
    return passthru

def _clear():
    """Clear functions caches (debug purpose)."""
    _build_diffuse.cache_clear()
    _build_fallback.cache_clear()
    _build_passthrough.cache_clear()
    _build_standard.cache_clear()
    _convert_passthru.cache_clear()


# Clear cache when reload module (debug)
_clear()
