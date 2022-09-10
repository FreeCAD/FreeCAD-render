# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
# *   Copyright (c) 2022 Howetuft <howetuft-at-gmail.com>                   *
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

"""Appleseed renderer plugin for FreeCAD Render workbench."""

# Suggested documentation links:
# https://github.com/appleseedhq/appleseed/wiki
# https://github.com/appleseedhq/appleseed/wiki/Built-in-Entities

# NOTE Appleseed uses a different coordinate system than FreeCAD.
# Y and Z are switched and Z is inverted

import os
import re
from tempfile import mkstemp
from math import degrees, radians, acos, atan2, sqrt
from textwrap import indent
import collections

import FreeCAD as App

TEMPLATE_FILTER = "Appleseed templates (appleseed_*.appleseed)"

SHADERS_DIR = os.path.join(os.path.dirname(__file__), "as_shaders")


# ===========================================================================
#                             Write functions
# ===========================================================================

# Transformation matrix from fcd coords to appleseed coords
TRANSFORM = App.Placement(
    App.Matrix(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1)
)


def write_mesh(name, mesh, material):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""

    # Compute material values
    matval = material.get_material_values(
        name, _write_texture, _write_value, _write_texref
    )

    # Get OBJ file
    #
    # NOTE 1: As Appleseed does not manage texture placement (translation,
    # rotation, scale), we have to transform uvmap... This is an approximate
    # approach. Moreover we have to choose one texture among all the material's
    # textures (but usually, there is only one). And we have to invert all the
    # transformation, as it applies to uv, not to texture
    #
    # NOTE 2: Appleseed does not look happy with FreeCAD normals
    # so we'll leave Appleseed compute them on its own (normals=False)
    #
    # NOTE 3: We should generate a special matval object for osl shader (with
    # specific _write_value, _write_texture and _write_texref functions).
    # This can be an enhancement in the future...

    texobjects = matval.texobjects
    if texobjects:
        tex = next(iter(texobjects.values()))  # We take the 1st texture...
        scale = 1.0 / float(tex.scale) if float(tex.scale) != 0 else 1.0
        rotation = -float(radians(tex.rotation))
        translation_u = -float(tex.translation_u)
        translation_v = -float(tex.translation_v)
        objfile = mesh.write_objfile(
            name,
            normals=False,
            uv_translate_u=translation_u,
            uv_translate_v=translation_v,
            uv_rotate=rotation,
            uv_scale=scale,
        )
    else:
        objfile = mesh.write_objfile(name, normals=False)

    # Compute transformation from FCD coordinates to Appleseed ones
    transform = TRANSFORM.copy()
    transform.multiply(mesh.Placement)
    transform.inverse()
    transfo_rows = [transform.Matrix.A[i * 4 : (i + 1) * 4] for i in range(4)]
    transfo_rows = [
        f"{r[0]:+15.8f} {r[1]:+15.8f} {r[2]:+15.8f} {r[3]:+15.8f}"
        for r in transfo_rows
    ]

    # Format output
    mat_name = matval.unique_matname  # Avoid duplicate materials
    shortfilename = os.path.splitext(os.path.basename(objfile))[0]
    filename = objfile.encode("unicode_escape").decode("utf-8")

    snippet_mat = _write_material(mat_name, matval)
    snippet_obj = f"""
            <object name="{shortfilename}" model="mesh_object">
                <parameter name="filename" value="{filename}" />
            </object>
            <object_instance name="{shortfilename}.{name}.instance"
                             object="{shortfilename}.{name}" >
                <transform>
                    <matrix>
                        {transfo_rows[0]}
                        {transfo_rows[1]}
                        {transfo_rows[2]}
                        {transfo_rows[3]}
                    </matrix>
                </transform>
                <assign_material
                    slot="default"
                    side="front"
                    material="{mat_name}"
                />
                <assign_material
                    slot="default"
                    side="back"
                    material="{mat_name}"
                />
            </object_instance>"""
    snippet_tex = matval.write_textures()

    snippet = snippet_tex + snippet_mat + snippet_obj

    return snippet


def write_camera(name, pos, updir, target, fov):
    """Compute a string in renderer SDL to represent a camera."""
    # This is where you create a piece of text in the format of
    # your renderer, that represents the camera.
    #
    # NOTE 'aspect_ratio' will be set at rendering time, when resolution is
    # known. So, at this stage, we just insert a macro-identifier named
    # @@ASPECT_RATIO@@, to be replaced by an actual value in 'render' function

    snippet = """
        <camera name="{n}" model="pinhole_camera">
            <parameter name="shutter_open_time" value="0" />
            <parameter name="shutter_close_time" value="1" />
            <parameter name="film_width" value="0.032" />
            <parameter name="aspect_ratio" value="@@ASPECT_RATIO@@" />
            <parameter name="focal_length" value="0" />
            <parameter name="horizontal_fov" value="{f}" />
            <transform>
                <look_at origin="{o.x} {o.y} {o.z}"
                         target="{t.x} {t.y} {t.z}"
                         up="{u.x} {u.y} {u.z}" />
            </transform>
        </camera>"""

    return snippet.format(
        n=name,
        o=_transform(pos.Base),
        t=_transform(target),
        u=_transform(updir),
        f=fov,
    )


def write_pointlight(name, pos, color, power):
    """Compute a string in renderer SDL to represent a point light."""
    # This is where you write the renderer-specific code
    # to export the point light in the renderer format
    snippet = """
            <!-- Object '{n}' -->
            <color name="{n}_color">
                <parameter name="color_space" value="srgb" />
                <parameter name="multiplier" value="1.0" />
                <parameter name="wavelength_range" value="400.0 700.0" />
                <values> {c[0]} {c[1]} {c[2]} </values>
                <alpha> 1.0 </alpha>
            </color>
            <light name="{n}" model="point_light">
                <parameter name="intensity" value="{n}_color" />
                <parameter name="intensity_multiplier" value="{p}" />
                <transform>
                    <translation value="{t.x} {t.y} {t.z}"/>
                </transform>
            </light>"""

    return snippet.format(
        n=name,
        c=color,
        p=power * 3,  # guesstimated factor...
        t=_transform(pos),
    )


def write_arealight(name, pos, size_u, size_v, color, power, transparent):
    """Compute a string in renderer SDL to represent an area light."""
    # Appleseed uses radiance (power/surface) instead of power
    radiance = power / (size_u * size_v)
    snippet = """
            <!-- Area light '{n}' -->
            <color name="{n}_color">
                <parameter name="color_space" value="srgb" />
                <parameter name="multiplier" value="1.0" />
                <parameter name="alpha" value="{g}" />
                <values> {c[0]} {c[1]} {c[2]} </values>
            </color>
            <edf name="{n}_edf" model="diffuse_edf">
                <parameter name="radiance" value="{n}_color" />
                <parameter name="radiance_multiplier" value="{p}" />
                <parameter name="exposure" value="0.0" />
                <parameter name="cast_indirect_light" value="true" />
                <parameter name="importance_multiplier" value="1.0" />
                <parameter name="light_near_start" value="0.0" />
            </edf>
            <material name="{n}_mat" model="generic_material">
                <parameter name="edf" value="{n}_edf" />
                <parameter name="bump_amplitude" value="1.0" />
                <parameter name="bump_offset" value="2.0" />
                <parameter name="displacement_method" value="bump" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="alpha_map" value="{g}" />
                <parameter name="shade_alpha_cutouts" value="false" />
            </material>
            <object name="{n}_obj" model="rectangle_object">
                <parameter name="width" value="{u}" />
                <parameter name="height" value="{v}" />
            </object>
            <object_instance name="{n}_obj.instance" object="{n}_obj">
                <transform>
                    <rotation axis="{r.x} {r.y} {r.z}" angle="{a}" />
                    <translation value="{t.x} {t.y} {t.z}" />
                </transform>
                <assign_material slot="default"
                                 side="front"
                                 material="{n}_mat" />
                <assign_material slot="default"
                                 side="back"
                                 material="{n}_mat" />
            </object_instance>"""
    return snippet.format(
        n=name,
        c=color,
        u=size_u,
        v=size_v,
        t=_transform(pos.Base),
        r=_transform(pos.Rotation.Axis),
        a=degrees(pos.Rotation.Angle),
        p=radiance / 100,  # guesstimated factor
        g=0.0 if transparent else 1.0,
    )


def write_sunskylight(name, direction, distance, turbidity, albedo):
    """Compute a string in renderer SDL to represent a sunsky light."""
    # Caution: Take Appleseed system of coordinates into account
    # From documentation: "Appleseed uses a right-handed coordinate system,
    # where X+ (positive X axis) points to the right, Y+ points upward
    # and Z+ points out of the screen, toward the viewer."
    vec = _transform(direction)
    phi = degrees(atan2(vec.z, vec.x))
    theta = degrees(acos(vec.y / (sqrt(vec.x**2 + vec.y**2 + vec.z**2))))

    snippet = """
        <environment_edf name="{n}_env_edf" model="hosek_environment_edf">
            <parameter name="sun_phi" value="{a}" />
            <parameter name="sun_theta" value="{b}" />
            <parameter name="turbidity" value="{t}" />
            <parameter name="ground_albedo" value="{g}" />
        </environment_edf>
        <environment_shader name="{n}_env_shdr" model="edf_environment_shader">
            <parameter name="environment_edf" value="{n}_env_edf" />
        </environment_shader>
        <environment name="{n}_env" model="generic_environment">
            <parameter name="environment_edf" value="{n}_env_edf" />
            <parameter name="environment_shader" value="{n}_env_shdr" />
        </environment>

            <!-- Sun_sky light '{n}' -->
            <light name="{n}" model="sun_light">
                <parameter name="environment_edf" value="{n}_env_edf" />
                <parameter name="turbidity" value="{t}" />
            </light>"""
    return snippet.format(n=name, a=phi, b=theta, t=turbidity, g=albedo)


def write_imagelight(name, image):
    """Compute a string in renderer SDL to represent an image-based light."""
    snippet = """
        <texture name="{n}_tex" model="disk_texture_2d">
            <parameter name="filename" value="{f}" />
            <parameter name="color_space" value="srgb" />
        </texture>
        <texture_instance name="{n}_tex_ins" texture="{n}_tex">
        </texture_instance>
        <environment_edf name="{n}_envedf" model="latlong_map_environment_edf">
            <parameter name="radiance" value="{n}_tex_ins" />
        </environment_edf>
        <environment_shader name="{n}_env_shdr" model="edf_environment_shader">
            <parameter name="environment_edf" value="{n}_envedf" />
        </environment_shader>
        <environment name="{n}_env" model="generic_environment">
            <parameter name="environment_edf" value="{n}_envedf" />
            <parameter name="environment_shader" value="{n}_env_shdr" />
        </environment>
    """
    return snippet.format(n=name, f=image)


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
            f"'{name}' - Material '{matval.shadertype}' unknown by renderer,"
            " using fallback material\n"
        )
        App.Console.PrintWarning(msg)
        snippet_mat = _write_material_fallback(name, matval.default_color)
    else:
        snippet_mat = write_function(name, matval)

    return snippet_mat


def _write_material_diffuse(name, matval, write_material=True):
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet_bsdf = f"""
            <bsdf name="{name}_bsdf" model="lambertian_brdf">
                <parameter name="reflectance" value="{matval["color"][0]}" />
            </bsdf>"""
    snippet_color = SNIPPET_COLOR.format(
        n=_color_name(name), c=matval["color"][1]
    )
    snippet = [snippet_color, snippet_bsdf]
    if write_material:
        snippet_material = _snippet_material(name, matval)
        snippet.append(snippet_material)
    return "".join(snippet)


def _write_material_glass(name, matval, write_material=True):
    """Compute a string in the renderer SDL for a glass material."""
    snippet_bsdf = f"""
            <bsdf name="{name}_bsdf" model="glass_bsdf">
                <parameter name="surface_transmittance"
                           value="{matval["color"][0]}" />
                <parameter name="ior" value="{matval["ior"]}" />
                <parameter name="roughness" value="0" />
                <parameter name="volume_parameterization"
                           value="transmittance" />
            </bsdf>"""
    snippet_color = SNIPPET_COLOR.format(
        n=_color_name(name), c=matval["color"][1]
    )
    snippet_material = SNIPPET_MATERIAL.format(n=name)
    snippet = [snippet_color, snippet_bsdf]
    if write_material:
        snippet_material = SNIPPET_MATERIAL.format(n=name)
        snippet.append(snippet_material)
    return "".join(snippet)


def _write_material_disney(name, matval):
    """Compute a string in the renderer SDL for a Disney material."""
    snippet_bsdf = f"""
            <bsdf name="{name}_bsdf" model="disney_brdf">
                <parameter name="base_color"
                           value="{matval["basecolor"][0]}" />
                <parameter name="subsurface"
                           value="{matval["subsurface"]}" />
                <parameter name="metallic"
                           value="{matval["metallic"]}" />
                <parameter name="specular"
                           value="{matval["specular"]}" />
                <parameter name="specular_tint"
                           value="{matval["speculartint"]}" />
                <parameter name="roughness"
                           value="{matval["roughness"]}" />
                <parameter name="anisotropic"
                           value="{matval["anisotropic"]}" />
                <parameter name="sheen"
                           value="{matval["sheen"]}" />
                <parameter name="sheen_tint"
                           value="{matval["sheentint"]}" />
                <parameter name="clearcoat"
                           value="{matval["clearcoat"]}" />
                <parameter name="clearcoat_gloss"
                           value="{matval["clearcoatgloss"]}" />
            </bsdf>"""
    snippet_color = SNIPPET_COLOR.format(
        n=_color_name(name), c=matval["basecolor"][1]
    )
    snippet_material = _snippet_material(name, matval)
    snippet = [snippet_color, snippet_bsdf, snippet_material]
    return "".join(snippet)


def _write_material_mixed(name, matval):
    """Compute a string in the renderer SDL for a Mixed material."""
    # Glass
    submat_g = matval.getmixedsubmat("glass", name + "_glass")
    snippet_g = _write_material_glass(f"{name}_glass", submat_g, False)
    snippet_g_tex = submat_g.write_textures()

    # Diffuse
    submat_d = matval.getmixedsubmat("diffuse", name + "_diffuse")
    snippet_d = _write_material_diffuse(f"{name}_diffuse", submat_d, False)
    snippet_d_tex = submat_d.write_textures()

    snippet_mixed = f"""
            <bsdf name="{name}_bsdf" model="bsdf_blend">
                <parameter name="bsdf0" value="{name}_glass_bsdf" />
                <parameter name="bsdf1" value="{name}_diffuse_bsdf" />
                <parameter name="weight"
                           value="{matval["transparency"]}" />
            </bsdf>"""

    snippet_material = _snippet_material(name, matval)
    snippet = [
        snippet_g_tex,
        snippet_d_tex,
        snippet_g,
        snippet_d,
        snippet_mixed,
        snippet_material,
    ]
    return "".join(snippet)


def _write_material_carpaint(name, matval):
    """Compute a string in the renderer SDL for a carpaint material."""
    # carpaint is an osl shader, so the computation is a bit more complex,
    # and not so 'industrialized' for textures as other shaders...
    path = SHADERS_DIR.encode("unicode_escape").decode("utf-8")

    # Base color
    color = matval["basecolor"][1]  # Base
    color_texobj = matval.get_texobject("basecolor")

    if color_texobj:  # Material has color texture
        filename = color_texobj.file.encode("unicode_escape").decode("utf-8")
        color_texshader = f"""
        <!-- Color texture -->
        <shader layer="BasecolorTex" type="shader" name="as_texture">
            <parameter name="in_filename"
                       value="string {filename}" />
        </shader>"""
        color_texconnect = """
        <connect_shaders src_layer="BasecolorTex" src_param="out_color"
                         dst_layer="MasterMix" dst_param="in_color" />
        <connect_shaders src_layer="BasecolorTex" src_param="out_color"
                         dst_layer="MasterMix" dst_param="in_specular_color" />
        <connect_shaders src_layer="BasecolorTex"
                         src_param="out_color"
                         dst_layer="MasterMix"
                         dst_param="in_coating_absorption" />"""
    else:
        color_texshader, color_texconnect = "", ""

    # Bump/Normal
    if matval.has_bump() and matval.has_normal():
        msg = (
            f"[Render] [Appleseed] [Material '{name}'] Warning - Appleseed "
            "does not support bump and normal at the same time in a material. "
            "Falling back to bump only.\n"
        )
        App.Console.PrintWarning(msg)

    if matval.has_bump():
        bump_texobj = matval.get_texobject("bump")
        filename = bump_texobj.file.encode("unicode_escape").decode("utf-8")
        normal_texshader = f"""
        <!-- Bump -->
        <shader layer="BumpTex" type="shader" name="as_texture">
            <parameter name="in_filename"
                       value="string {filename}" />
        </shader>
        <shader layer="Bump" type="shader" name="as_bump">
            <parameter name="in_mode" value="string Bump" />
            <parameter name="in_bump_depth" value="float 1.0" />
        </shader>"""
        normal_texconnect = f"""
        <connect_shaders src_layer="BumpTex" src_param="out_channel"
                         dst_layer="Bump" dst_param="in_bump_value" />
        <connect_shaders src_layer="Bump"
                         src_param="out_normal"
                         dst_layer="MasterMix"
                         dst_param="in_bump_normal_substrate" />"""
    elif matval.has_normal():
        normal_texshader = f"""
        <!-- Normal -->
        <shader layer="NormalTex" type="shader" name="as_texture">
            <parameter name="in_filename"
                       value="string {filename}" />
        </shader>
        <shader layer="SubstrateBump" type="shader" name="as_bump">
            <parameter name="in_mode" value="string Normal Map" />
            <parameter name="in_normal_map_weight" value="float 0.4" />
            <parameter name="in_normal_map_swap_rg" value="int 0" />
            <parameter name="in_normal_map_coordsys" value="string Tangent Space" />
            <parameter name="in_normal_map_mode" value="string Unsigned" />
        </shader>
        <shader layer="CoatingBump" type="shader" name="as_bump">
            <parameter name="in_mode" value="string Normal Map" />
            <parameter name="in_normal_map_weight" value="float 0.4" />
            <parameter name="in_normal_map_swap_rg" value="int 0" />
            <parameter name="in_normal_map_coordsys" value="string Tangent Space" />
            <parameter name="in_normal_map_mode" value="string Unsigned" />
        </shader>"""
        normal_texconnect = f"""
        <connect_shaders src_layer="NormalTex" src_param="out_color"
                         dst_layer="SubstrateBump" dst_param="in_normal_map" />
        <connect_shaders src_layer="NormalTex" src_param="out_color"
                         dst_layer="CoatingBump" dst_param="in_normal_map" />
        <connect_shaders src_layer="SubstrateBump"
                         src_param="out_normal"
                         dst_layer="MasterMix"
                         dst_param="in_bump_normal_substrate" />
        <connect_shaders src_layer="CoatingBump"
                         src_param="out_normal"
                         dst_layer="MasterMix"
                         dst_param="in_bump_normal_coating" />"""
    else:
        normal_texshader = ""
        normal_texconnect = f"""
        """

    # Final consolidation
    snippet = f"""
        <search_path>
            {path}
        </search_path>
    <!-- Carpaint Shader -->
    <material name="{name}" model="osl_material">
        <parameter name="surface_shader" value="{name}_ss" />
        <parameter name="osl_surface" value="{name}_group" />
    </material>

    <surface_shader name="{name}_ss" model="physical_surface_shader" />

    <shader_group name="{name}_group">
{color_texshader}{normal_texshader}
        <shader layer="MasterMix" type="shader" name="as_standard_surface">
            <parameter name="in_color"
                       value="color {color}" />
            <parameter name="in_diffuse_weight"
                       value="float 0.8" />
            <parameter name="in_specular_color"
                       value="color {color}" />
            <parameter name="in_specular_roughness"
                       value="float 0.8" />
            <parameter name="in_fresnel_type"
                       value="int 1" />
            <parameter name="in_face_tint"
                       value="color 231 233 235" />
            <parameter name="in_edge_tint"
                       value="color 212 219 227" />
            <parameter name="in_edge_tint_weight"
                       value="float 0.1" />
            <parameter name="in_coating_absorption"
                       value="color {color}" />
            <parameter name="in_coating_reflectivity"
                       value="float 0.8" />
            <parameter name="in_coating_roughness"
                       value="float 0.1" />
            <parameter name="in_coating_depth"
                       value="float 0.001" />
            <parameter name="in_coating_ior"
                       value="float 1.57" />
        </shader>
        <shader layer="Surface" type="surface" name="as_closure2surface" />
{color_texconnect}{normal_texconnect}
        <connect_shaders src_layer="MasterMix" src_param="out_outColor"
                         dst_layer="Surface" dst_param="in_input" />
    </shader_group>"""

    return snippet


def _write_material_passthrough(name, matval):
    """Compute a string in the renderer SDL for a passthrough material."""
    snippet = indent(matval["string"], "    ")
    return snippet.format(n=name, c=matval.default_color)


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
        red, grn, blu = 1.0, 1.0, 1.0

    color = RGB(red, grn, blu)

    snippet = (
        SNIPPET_COLOR.format(
            n=_color_name(name), c=f"{color.r} {color.g} {color.b}"
        ),
        f"""
            <!-- Object '{name}' - FALLBACK -->
            <bsdf name="{name}_bsdf" model="lambertian_brdf">
                <parameter name="reflectance" value="{_color_name(name)}" />
            </bsdf>
            <material name="{name}" model="generic_material">
                <parameter name="bsdf" value="{name}_bsdf" />
            </material>""",
    )
    return "".join(snippet)


MATERIALS = {
    "Passthrough": _write_material_passthrough,
    "Glass": _write_material_glass,
    "Disney": _write_material_disney,
    "Diffuse": _write_material_diffuse,
    "Mixed": _write_material_mixed,
    "Carpaint": _write_material_carpaint,
}

SNIPPET_COLOR = """
            <color name="{n}">
                <parameter name="color_space" value="srgb" />
                <parameter name="multiplier" value="1.0" />
                <parameter name="wavelength_range" value="400.0 700.0" />
                <values> {c} </values>
            </color>"""

SNIPPET_MATERIAL = """
            <material name="{n}" model="generic_material">
                <parameter name="bsdf" value="{n}_bsdf" />
                <parameter name="bump_amplitude" value="1.0" />
                <parameter name="bump_offset" value="2.0" />
                <parameter name="displacement_method" value="bump" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="shade_alpha_cutouts" value="false" />
            </material>"""

RGB = collections.namedtuple("RGB", "r g b")


def _snippet_material(name, matval):
    """Get a string for Appleseed Material entity."""
    if matval.has_bump() and matval.has_normal():
        msg = (
            f"[Render] [Appleseed] [Material '{name}'] Warning - Appleseed "
            "does not support bump and normal at the same time in a material. "
            "Falling back to bump only.\n"
        )
        App.Console.PrintWarning(msg)

    if matval.has_bump():
        disp_method = "bump"
        disp_map = matval["bump"]
    elif matval.has_normal():
        disp_method = "normal"
        disp_map = matval["normal"]
    else:
        # No bump, no normal: return simple material
        return f"""
            <material name="{name}" model="generic_material">
                <parameter name="bsdf" value="{name}_bsdf" />
            </material>"""

    snippet = f"""
            <material name="{name}" model="generic_material">
                <parameter name="bsdf" value="{name}_bsdf" />
                <parameter name="displacement_method" value="{disp_method}" />
                <parameter name="displacement_map" value="{disp_map}" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="bump_amplitude" value="0.001" />
                <parameter name="default_tangent_mode" value="uv" />
            </material>"""
    return snippet


# ===========================================================================
#                             Textures
# ===========================================================================


def _texname(**kwargs):
    """Compute texture name (helper)."""
    propname = kwargs["propname"]
    unique_matname = kwargs["unique_matname"]
    texname = f"{unique_matname}.{propname}.tex"
    return texname


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
    # Retrieve parameters
    propvalue = kwargs["propvalue"]
    proptype = kwargs["proptype"]

    # Compute texture name
    texname = _texname(**kwargs)

    # Compute file name
    filename = propvalue.file.encode("unicode_escape").decode("utf-8")

    # Texture
    colorspace = "srgb" if proptype == "RGB" else "linear_rgb"
    texture = f"""
        <texture name="{texname}" model="disk_texture_2d">
            <parameter name="filename" value="{filename}"/>
            <parameter name="color_space" value="{colorspace}"/>
        </texture>
        <texture_instance name="{texname}.instance" texture="{texname}">
        </texture_instance>"""

    return texname, texture


def _write_value(**kwargs):
    """Compute a string in renderer SDL from a shader property value.

    Args:
        proptype -- Shader property's type
        propvalue -- Shader property's value

    The result depends on the type of the value...
    """
    # Retrieve parameters
    proptype = kwargs["proptype"]
    val = kwargs["propvalue"]
    matname = kwargs["unique_matname"]

    # Snippets for values
    if proptype == "RGB":
        value = (
            _color_name(matname),
            f"{val.r:.8} {val.g:.8} {val.b:.8}",
        )
    elif proptype == "float":
        value = f"{val:.8}"
    elif proptype == "node":
        value = ""
    elif proptype == "texonly":
        value = f"{val}"
    elif proptype == "str":
        value = f"{val}"
    else:
        raise NotImplementedError

    return value


def _write_texref(**kwargs):
    """Compute a string in SDL for a reference to a texture in a shader."""
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]

    texref = f"{_texname(**kwargs)}.instance"

    # IOR special case
    if propname == "ior":
        msg = (
            "[Render] [Appleseed] Warning - Appleseed does not support "
            "textures for 'ior' parameter. Fallback to value 1.5\n"
        )
        App.Console.PrintWarning(msg)
        return "1.5"

    # RGB special case
    if proptype == "RGB":
        return (texref, "0.8 0.8 0.8")

    return texref


def _color_name(matname):
    """Make a color name (helper).

    This function gives a common name computation for color snippet,
    texture and bsdf functions, to avoid discrepancies.

    Args:
    matname -- Material name
    """
    return f"{matname}_color"


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

    def move_elements(element_tag, destination, template, keep_one=False):
        """Move elements into another (root) element.

        If keep_one is set, only last element is kept.
        """
        pattern = r"(?m)^ *<{e}(?:\s.*|)>[\s\S]*?<\/{e}>\n".format(
            e=element_tag
        )
        regex_obj = re.compile(pattern)
        contents = (
            str(regex_obj.findall(template)[-1])
            if keep_one
            else "\n".join(regex_obj.findall(template))
        )
        template = regex_obj.sub("", template)
        pos = re.search(rf"<{destination}>\n", template).end()
        template = template[:pos] + contents + "\n" + template[pos:]
        return template

    # Here you trigger a render by firing the renderer
    # executable and passing it the needed arguments, and
    # the file it needs to render

    # Make various adjustments on file:
    # Change image size in template, adjust camera ratio, reorganize cameras
    # declarations and specify default camera

    # Before all, open result file
    with open(project.PageResult, "r", encoding="utf-8") as f:
        template = f.read()

    # Gather cameras, environment_edf, environment_shader, environment elements
    # in scene block (keeping only one environment element)
    template = move_elements("camera", "scene", template)
    template = move_elements("environment_edf", "scene", template)
    template = move_elements("environment_shader", "scene", template)
    template = move_elements("environment", "scene", template, True)
    template = move_elements("texture", "scene", template)
    template = move_elements("texture_instance", "scene", template)
    template = move_elements("search_path", "search_paths", template)

    # Change image size
    res = re.findall(r"<parameter name=\"resolution.*?\/>", template)
    if res:
        snippet = '<parameter name="resolution" value="{} {}"/>'
        template = template.replace(res[0], snippet.format(width, height))

    # Adjust cameras aspect ratio, in accordance with width & height
    aspect_ratio = width / height if height else 1.0
    template = template.replace("@@ASPECT_RATIO@@", str(aspect_ratio))

    # Define default camera
    res = re.findall(r"<camera name=\"(.*?)\".*?>", template)
    if res:
        default_cam = res[-1]  # Take last match
        snippet = '<parameter name="camera" value="{}" />'
        template = re.sub(
            r"<parameter\s+name\s*=\s*\"camera\"\s+value\s*=\s*\"(.*?)\"\s*/>",
            snippet.format(default_cam),
            template,
        )

    # Write resulting output to file
    f_handle, f_path = mkstemp(
        prefix=project.Name, suffix=os.path.splitext(project.Template)[-1]
    )
    os.close(f_handle)
    with open(f_path, "w", encoding="utf-8") as f:
        f.write(template)
    project.PageResult = f_path
    os.remove(f_path)

    # Prepare parameters
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    if external:
        rpath = params.GetString("AppleseedStudioPath", "")
        args = ""
    else:
        rpath = params.GetString("AppleseedCliPath", "")
        args = params.GetString("AppleseedParameters", "")
        if args:
            args += " "
        args += "--output " + output
    if not rpath:
        App.Console.PrintError(
            "Unable to locate renderer executable. "
            "Please set the correct path in "
            "Edit -> Preferences -> Render\n"
        )
        return None, None
    if args:
        args += " "

    filepath = f'"{project.PageResult}"'

    # Build Appleseed command
    cmd = prefix + rpath + " " + args + " " + filepath + "\n"

    # Return cmd, output
    # output is None, as no resulting image is output by Appleseed
    return cmd, None


# ===========================================================================
#                                Utilities
# ===========================================================================


def _transform(vec):
    """Convert a vector from FreeCAD coordinates into Appleseed ones.

    Appleseed uses a different coordinate system than FreeCAD.
    Compared to FreeCAD, Y and Z are switched and Z is inverted.
    This function converts a vector from FreeCAD system to Appleseed one.

    Args:
        vec -- vector to convert, in FreeCAD coordinates

    Returns:
        The transformed vector, in Appleseed coordinates
    """
    return App.Vector(vec.x, vec.z, -vec.y)
