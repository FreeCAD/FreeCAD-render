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
from collections import namedtuple

import FreeCAD as App

from Render.utils import (
    RGBA,
    str2rgb,
    parse_csv_str,
    debug as ru_debug,
    getproxyattr,
    translate,
)
from Render.texture import str2imageid


# ===========================================================================
#                                   Export
# ===========================================================================

Param = collections.namedtuple("Param", "name type default desc")

# IMPORTANT: Please note that, by convention, the first parameter of each
# material will be used as default color in fallback mechanisms.
# Please be careful to preserve a color-typed field as first parameter of each
# material, if you modify an existing material or you add a new one...
STD_MATERIALS_PARAMETERS = {
    "Glass": [
        Param(
            "Color", "RGB", (1, 1, 1), translate("Render", "Transmitted color")
        ),
        Param("IOR", "float", 1.5, translate("Render", "Index of refraction")),
    ],
    "Disney": [
        Param(
            "BaseColor",
            "RGB",
            (0.8, 0.8, 0.8),
            translate("Render", "Base color"),
        ),
        Param(
            "Subsurface",
            "float",
            0.0,
            translate("Render", "Subsurface coefficient"),
        ),
        Param(
            "Metallic",
            "float",
            0.0,
            translate("Render", "Metallic coefficient"),
        ),
        Param(
            "Specular",
            "float",
            0.0,
            translate("Render", "Specular coefficient"),
        ),
        Param(
            "SpecularTint",
            "float",
            0.0,
            translate("Render", "Specular tint coefficient"),
        ),
        Param(
            "Roughness",
            "float",
            0.0,
            translate("Render", "Roughness coefficient"),
        ),
        Param(
            "Anisotropic",
            "float",
            0.0,
            translate("Render", "Anisotropic coefficient"),
        ),
        Param("Sheen", "float", 0.0, translate("Render", "Sheen coefficient")),
        Param(
            "SheenTint",
            "float",
            0.0,
            translate("Render", "Sheen tint coefficient"),
        ),
        Param(
            "ClearCoat",
            "float",
            0.0,
            translate("Render", "Clear coat coefficient"),
        ),
        Param(
            "ClearCoatGloss",
            "float",
            0.0,
            translate("Render", "Clear coat gloss coefficient"),
        ),
    ],
    "Diffuse": [
        Param(
            "Color",
            "RGB",
            (0.8, 0.8, 0.8),
            translate("Render", "Diffuse color"),
        )
    ],
    # NB: Above 'Mixed' material could be extended with reflectivity in the
    # future, with the addition of a Glossy material. See for instance:
    # https://download.blender.org/documentation/bc2012/FGastaldo_PhysicallyCorrectshading.pdf
    "Mixed": [
        Param(
            "Diffuse.Color",
            "RGB",
            (0.8, 0.8, 0.8),
            translate("Render", "Diffuse color"),
        ),
        Param(
            "Glass.Color",
            "RGB",
            (1, 1, 1),
            translate("Render", "Transmitted color"),
        ),
        Param(
            "Glass.IOR",
            "float",
            1.5,
            translate("Render", "Index of refraction"),
        ),
        Param(
            "Transparency",
            "float",
            0.5,
            translate(
                "Render",
                "Mix ratio between Glass and Diffuse "
                "(should stay in [0,1], other values "
                "may lead to undefined behaviour)",
            ),
        ),
    ],
    "Carpaint": [
        Param(
            "BaseColor",
            "RGB",
            (0.8, 0.2, 0.2),
            translate("Render", "Base color"),
        ),
    ],
}


STD_MATERIALS = sorted(list(STD_MATERIALS_PARAMETERS.keys()))


RendererTexture = namedtuple(
    "RendererTexture",
    "file rotation scale_u scale_v translation_u translation_v",
)


def _castrgb(value, objcol):
    """Cast extended RGB field value to RGB object or RendererTexture object.

    This function can handle "object color" special case:
    'value' is treated as a semicolon separated value.
    if 'value' contains "Object", 'objcol' is returned

    Args:
        value -- the value to parse and cast
        objcol -- the object color

    Returns:
        a RGB object containing the targeted color **or** a RendererTexture
        object if appliable.
    """
    parsed = parse_csv_str(value)
    if "Object" in parsed:
        return objcol
    elif "Texture" in parsed:
        # Build RendererTexture
        imageid = str2imageid(parsed[1])
        texobject = App.ActiveDocument.getObject(
            imageid.texture
        )  # Texture object
        file = texobject.getPropertyByName(imageid.image)
        res = RendererTexture(
            file,
            texobject.Rotation,
            texobject.ScaleU,
            texobject.ScaleV,
            texobject.TranslationU,
            texobject.TranslationV,
        )
        print(res)  # TODO
        return res
    else:
        # Default case, return color
        return str2rgb(parsed[0])


CAST_FUNCTIONS = {
    "float": lambda x, y: float(x) if x else 0.0,
    "RGB": _castrgb,
    "string": lambda x, y: str(x),
}


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
            debug(f"Unknown material type '{shadertype}'")
        else:
            values = tuple(
                (
                    p.name,  # Parameter name
                    mat.get(f"Render.{shadertype}.{p.name}", None),  # Par val
                    p.default,  # Parameter default value
                    p.type,  # Parameter type
                    default_color,  # Object color
                )
                for p in params
            )
            return _build_standard(shadertype, values)

    # Climb up to Father
    debug("No valid material definition - trying father material")
    try:
        father_name = mat["Father"]
        assert father_name
        materials = (
            o for o in App.ActiveDocument.Objects if is_valid_material(o)
        )
        father = next(
            m for m in materials if m.Material.get("Name", "") == father_name
        )
    except (KeyError, AssertionError):
        # No father
        debug("No valid father")
    except StopIteration:
        # Found father, but not in document
        msg = (
            "Found father material name ('{}') but "
            "did not find this material in active document"
        )
        debug(msg.format(father_name))
    else:
        # Found usable father
        debug(f"Retrieve father material '{father_name}'")
        return get_rendering_material(father, renderer, default_color)

    # Try with Coin-like parameters (backward compatibility)
    try:
        diffusecolor = str2rgb(mat["DiffuseColor"])
    except (KeyError, TypeError):
        pass
    else:
        debug("Fallback to Coin-like parameters")
        color = RGBA(
            diffusecolor.r,
            diffusecolor.g,
            diffusecolor.b,
            float(mat.get("Transparency", "0")) / 100,
        )
        return _build_fallback(color)

    # Fallback with default_color
    debug("Fallback to default color")
    return _build_fallback(default_color)


@functools.lru_cache(maxsize=128)
def passthrough_keys(renderer):
    """Compute material card keys for passthrough rendering material."""
    return {f"Render.{renderer}.{i:04}" for i in range(1, 9999)}


def is_multimat(obj):
    """Check if a material is a multimaterial."""
    try:
        is_app_feature = obj.isDerivedFrom("App::FeaturePython")
    except AttributeError:
        return False

    is_type_multimat = getproxyattr(obj, "Type", None) == "MultiMaterial"

    return obj is not None and is_app_feature and is_type_multimat


def generate_param_doc():
    """Generate Markdown documentation from material rendering parameters."""
    header_fmt = [
        "#### **{m}** Material",
        "",
        "`Render.Type={m}`",
        "",
        "Parameter | Type | Default value | Description",
        "--------- | ---- | ------------- | -----------",
    ]

    line_fmt = "`Render.{m}.{p.name}` | {p.type} | {p.default} | {p.desc}"
    footer_fmt = [""]
    lines = []
    for mat in STD_MATERIALS:
        lines += [h.format(m=mat) for h in header_fmt]
        lines += [
            line_fmt.format(m=mat, p=param)
            for param in STD_MATERIALS_PARAMETERS[mat]
        ]
        lines += footer_fmt

    return "\n".join(lines)


def is_valid_material(obj):
    """Assert that an object is a valid Material."""
    try:
        is_materialobject = obj.isDerivedFrom("App::MaterialObjectPython")
    except AttributeError:
        return False

    return (
        obj is not None
        and is_materialobject
        and hasattr(obj, "Material")
        and isinstance(obj.Material, dict)
    )


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
        return f"{type(self).__name__}({', '.join(items)})"

    def setshaderparam(self, name, value):
        """Set shader parameter.

        If parameter does not exist, add it.
        If parameter name is a compound like 'foo.bar.baz', foo and bar are
        added as SimpleNamespaces.
        """
        path = [e.lower() for e in [self.shadertype] + name.split(".")]
        res = self
        for elem in path[:-1]:
            if not hasattr(res, elem):
                setattr(res, elem, types.SimpleNamespace())
            res = getattr(res, elem)
        setattr(res, path[-1], value)

    def getshaderparam(self, name):
        """Get shader parameter.

        If parameter name is a compound like 'foo.bar.baz', the method
        retrieves self.foo.bar.baz .
        If one of the path element is missing in self, an AttributeError will
        be raised.
        """
        path = [e.lower() for e in [self.shadertype] + name.split(".")]
        res = self
        for elem in path:
            res = getattr(res, elem)
        return res

    @property
    def shader(self):
        """Get shader attribute, whatever underlying attribute it is."""
        return getattr(self, self.shadertype.lower())


@functools.lru_cache(maxsize=128)
def _build_standard(shadertype, values):
    """Build standard material."""
    res = RenderMaterial(shadertype)

    for nam, val, dft, typ, objcol in values:
        cast_function = CAST_FUNCTIONS[typ]
        try:
            value = cast_function(val, objcol)
        except TypeError:
            value = cast_function(str(dft), objcol)
        res.setshaderparam(nam, value)

    # Add a default_color, for fallback mechanisms in renderers.
    # By convention, the default color must be in the first parameter of the
    # material.
    par = STD_MATERIALS_PARAMETERS[shadertype][0]
    res.default_color = res.getshaderparam(par.name)
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
        _color = ",".join([str(c) for c in color[:3]])
        _alpha = str(color[3])
    except IndexError:
        _color = "0.8, 0.8, 0.8"
        _alpha = "0.0"
    finally:
        _rgbcolor = str2rgb(_color)

    # A simpler approach would have been to rely only on mixed material but it
    # leads to a lot of materials definitions in output files which hinders the
    # proper functioning of most of the renderers, so we implement a more
    # selective operation.
    if float(_alpha) == 0:
        # Build diffuse
        shadertype = "Diffuse"
        values = (("Color", _color, _color, "RGB", _rgbcolor),)
    elif float(_alpha) == 1:
        # Build glass
        shadertype = "Glass"
        values = (
            ("IOR", "1.5", "1.5", "float", _rgbcolor),
            ("Color", _color, _color, "RGB", _rgbcolor),
        )
    else:
        # Build mixed
        shadertype = "Mixed"
        values = (
            ("Diffuse.Color", _color, _color, "RGB", _rgbcolor),
            ("Glass.IOR", "1.5", "1.5", "float", _rgbcolor),
            ("Glass.Color", _color, _color, "RGB", _rgbcolor),
            ("Transparency", _alpha, _alpha, "float", _rgbcolor),
        )

    return _build_standard(shadertype, values)


def _get_float(material, param_prefix, param_name, default=0.0):
    """Get float value in material dictionary."""
    return material.get(param_prefix + param_name, default)


PASSTHRU_REPLACED_TOKENS = (
    ("{", "{{"),
    ("}", "}}"),
    ("%NAME%", "{n}"),
    ("%RED%", "{c.r}"),
    ("%GREEN%", "{c.g}"),
    ("%BLUE%", "{c.b}"),
)


@functools.lru_cache(maxsize=128)
def _convert_passthru(passthru):
    """Convert a passthrough string from FCMat format to Python FSML.

    (FSML stands for Format Specification Mini-Language)
    """
    for token in PASSTHRU_REPLACED_TOKENS:
        passthru = passthru.replace(*token)
    return passthru


def printmat(fcdmat):
    """Print a rendering material to a string, in Material Card format.

    This function allows to rebuild a Material Card content from a FreeCAD
    material object, for the Render part.

    Args:
        fcdmat -- a FreeCAD material object (App::MaterialObjectPython)

    Returns:
        a string containing the material in Material Card format
    """

    def keysort(item):
        key, _, keyword = item
        if keyword == "Type":
            rank = 0
        elif keyword in STD_MATERIALS_PARAMETERS:
            rank = 1
        else:
            rank = 2
        return (rank, key)

    items = [
        (i[0], i[1], i[0].split(".")[1])
        for i in fcdmat.Material.items()
        if i[0].startswith("Render.")
    ]
    items.sort(key=keysort)
    lines = [f"{i[0]} = {i[1]}" for i in items]
    print("\n".join(lines))


def _clear():
    """Clear functions caches (debug purpose)."""
    _build_fallback.cache_clear()
    _build_passthrough.cache_clear()
    _build_standard.cache_clear()
    _convert_passthru.cache_clear()


# Clear cache when reload module (debug)
_clear()
