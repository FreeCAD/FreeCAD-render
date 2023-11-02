# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
# *   Copyright (c) 2022 Howetuft <howetuft-at-gmail.com>                   *
# *   Copyright (c) 2023 Howetuft <howetuft-at-gmail.com>                   *
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
#
# FreeCAD (z is up):         Appleseed (y is up):
#
#
#  z  y                         y
#  | /                          |
#  .--x                         .--x
#                              /
#                             z

import os
import re
from textwrap import indent
from math import degrees, acos, atan2, sqrt
import collections
import xml.etree.ElementTree as et
import xml.dom.minidom

import FreeCAD as App

from .utils.misc import fovy_to_fovx

TEMPLATE_FILTER = "Appleseed templates (appleseed_*.appleseed)"

SHADERS_DIR = os.path.join(os.path.dirname(__file__), "as_shaders")


# ===========================================================================
#                             Write functions
# ===========================================================================

# Transformation matrix from fcd coords to appleseed coords
PLACEMENT = App.Placement(
    App.Matrix(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1)
)


def write_mesh(name, mesh, material, **kwargs):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""

    # Compute material values
    matval = material.get_material_values(
        name,
        _write_texture,
        _write_value,
        _write_texref,
        kwargs["project_directory"],
    )

    # Get OBJ file
    objfile = mesh.write_file(name, mesh.ExportType.OBJ)

    # Compute OBJ transformation
    # including transfo from FCD coordinates to Appleseed ones
    mesh.transformation.apply_placement(PLACEMENT, left=True)
    transfo_rows = [
        (
            "<dummy>"
            f"{r[0]:+15.8f} {r[1]:+15.8f} {r[2]:+15.8f} {r[3]:+15.8f}"
            "</dummy>"
        )
        for r in mesh.transformation.get_matrix_rows()
    ]

    # Format output
    mat_name = matval.unique_matname  # Avoid duplicate materials
    shortfilename, _ = os.path.splitext(os.path.basename(objfile))
    filename = objfile.encode("unicode_escape").decode("utf-8")

    snippet_mat = _write_material(mat_name, matval)
    snippet_obj = f"""
            <object name="{shortfilename}" model="mesh_object">
                <parameter name="filename" value="{filename}" />
            </object>
            <object_instance name="{shortfilename}.instance"
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

    snippet = snippet_mat + snippet_obj

    return snippet


def write_camera(name, pos, updir, target, fov, resolution, **kwargs):
    """Compute a string in renderer SDL to represent a camera."""
    orig = _transform(pos.Base)
    target = _transform(target)
    updir = _transform(updir)
    width, height = resolution
    aspect_ratio = width / height

    # Appleseed expects horizontal fov, so we have to convert
    fov = fovy_to_fovx(fov, *resolution)

    snippet = f"""
        <camera name="{name}" model="pinhole_camera">
            <parameter name="film_width" value="0.032" />
            <parameter name="aspect_ratio" value="{aspect_ratio}" />
            <parameter name="horizontal_fov" value="{fov}" />
            <transform>
                <look_at origin="{orig.x} {orig.y} {orig.z}"
                         target="{target.x} {target.y} {target.z}"
                         up="{updir.x} {updir.y} {updir.z}" />
            </transform>
        </camera>"""

    return snippet


def write_pointlight(name, pos, color, power, **kwargs):
    """Compute a string in renderer SDL to represent a point light."""
    # This is where you write the renderer-specific code
    # to export the point light in the renderer format
    snippet = """
            <!-- Object '{n}' -->
            <color name="{n}_color">
                <parameter name="color_space" value="linear_rgb" />
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
        c=color.to_linear(),
        p=power * 3,  # guesstimated factor...
        t=_transform(pos),
    )


def write_arealight(
    name, pos, size_u, size_v, color, power, transparent, **kwargs
):
    """Compute a string in renderer SDL to represent an area light."""
    # Appleseed uses radiance (power/surface) instead of power
    radiance = power / (size_u * size_v)
    snippet = """
            <!-- Area light '{n}' -->
            <color name="{n}_color">
                <parameter name="color_space" value="linear_rgb" />
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
        c=color.to_linear(),
        u=size_u,
        v=size_v,
        t=_transform(pos.Base),
        r=_transform(pos.Rotation.Axis),
        a=degrees(pos.Rotation.Angle),
        p=radiance / 100,  # guesstimated factor
        g=0.0 if transparent else 1.0,
    )


def write_sunskylight(
    name,
    direction,
    distance,
    turbidity,
    albedo,
    sun_intensity,
    sky_intensity,
    **kwargs,
):
    """Compute a string in renderer SDL to represent a sunsky light."""
    # Caution: Take Appleseed system of coordinates into account
    # From documentation: "Appleseed uses a right-handed coordinate system,
    # where X+ (positive X axis) points to the right, Y+ points upward
    # and Z+ points out of the screen, toward the viewer."
    vec = _transform(direction)
    phi = degrees(atan2(vec.z, vec.x))
    theta = degrees(acos(vec.y / (sqrt(vec.x**2 + vec.y**2 + vec.z**2))))

    sun_strength = 1.0 * sun_intensity
    sky_strength = 2.0 * sky_intensity

    snippet = f"""
        <environment_edf name="{name}_env_edf" model="hosek_environment_edf">
            <parameter name="sun_phi" value="{phi}" />
            <parameter name="sun_theta" value="{theta}" />
            <parameter name="turbidity" value="{turbidity}" />
            <parameter name="ground_albedo" value="{albedo}" />
            <parameter name="luminance_multiplier" value="{sky_strength}" />
        </environment_edf>
        <environment_shader name="{name}_env_shdr" model="edf_environment_shader">
            <parameter name="environment_edf" value="{name}_env_edf" />
        </environment_shader>
        <environment name="{name}_env" model="generic_environment">
            <parameter name="environment_edf" value="{name}_env_edf" />
            <parameter name="environment_shader" value="{name}_env_shdr" />
        </environment>

            <!-- Sun_sky light '{name}' -->
            <light name="{name}" model="sun_light">
                <parameter name="environment_edf" value="{name}_env_edf" />
                <parameter name="turbidity" value="{turbidity}" />
                <parameter name="radiance_multiplier" value="{sun_strength}" />
            </light>"""
    return snippet


def write_imagelight(name, image, **_):
    """Compute a string in renderer SDL to represent an image-based light."""
    snippet = """
        <scene_texture name="{n}_tex" model="disk_texture_2d">
            <parameter name="filename" value="{f}" />
            <parameter name="color_space" value="linear_rgb" />
        </scene_texture>
        <scene_texture_instance name="{n}_tex_ins" texture="{n}_tex">
        </scene_texture_instance>
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


def write_distantlight(
    name,
    color,
    power,
    direction,
    angle,
    **kwargs,
):
    """Compute a string in renderer SDL to represent a distant light."""
    # Nota: 'angle' is not suppported by Appleseed
    snippet = """
            <!-- Object '{n}' -->
            <color name="{n}_color">
                <parameter name="color_space" value="linear_rgb" />
                <parameter name="multiplier" value="1.0" />
                <parameter name="wavelength_range" value="400.0 700.0" />
                <values> {c[0]} {c[1]} {c[2]} </values>
                <alpha> 1.0 </alpha>
            </color>
            <light name="{n}" model="directional_light">
                <parameter name="color_space" value="linear_rgb" />
                <parameter name="irradiance" value="{n}_color" />
                <parameter name="irradiance_multiplier" value="{p}" />
                <transform>
                  <look_at origin="0 0 0" target="{t[0]} {t[1]} {t[2]}" up="0 1 0"/>
                </transform>
            </light>
"""
    return snippet.format(
        n=name,
        c=color.to_linear(),
        p=power,
        t=_transform(direction),
    )
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
            " using fallback material"
        )
        _warn(msg)
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
        snippet_tex = matval.write_textures()
        snippet += [snippet_tex, snippet_material]
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
    snippet = [snippet_color, snippet_bsdf]
    if write_material:
        snippet_material = _snippet_material(name, matval)
        snippet_tex = matval.write_textures()
        snippet += [snippet_tex, snippet_material]
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
    snippet_tex = matval.write_textures()
    snippet = [snippet_tex, snippet_color, snippet_bsdf, snippet_material]
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
    snippet_tex = matval.write_textures()
    snippet = [
        snippet_g_tex,
        snippet_d_tex,
        snippet_g,
        snippet_d,
        snippet_mixed,
        snippet_tex,
        snippet_material,
    ]
    return "".join(snippet)


def _write_material_carpaint(name, matval):
    """Compute a string in the renderer SDL for a carpaint material."""
    # carpaint is an osl shader
    path = SHADERS_DIR.encode("unicode_escape").decode("utf-8")

    # Base color
    color_texconnect, color = matval["basecolor"]

    # Bump/Normal
    if matval.has_bump():
        bump_texconnect, _ = matval["bump"]
    else:
        bump_texconnect = ""
    if matval.has_normal():
        normal_texconnect, _ = matval["normal"]
    else:
        normal_texconnect = ""

    # Final consolidation
    snippet_tex = matval.write_textures()
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
{snippet_tex}
        <shader layer="NormalMix" type="shader" name="fc_add_normal" >
            <parameter name="in_base_normal_mode" value="string Signed" />
            <parameter name="in_detail_normal_mode" value="string Signed" />
            <parameter name="in_detail_normal_weight" value="float 1.0" />
        </shader>
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
{color_texconnect}{bump_texconnect}{normal_texconnect}
        <!-- Connect normal mix to master -->
        <connect_shaders
            src_layer="NormalMix" src_param="out_normal"
            dst_layer="MasterMix" dst_param="in_bump_normal_substrate"
        />
        <!-- Connect to surface -->
        <connect_shaders src_layer="MasterMix" src_param="out_outColor"
                         dst_layer="Surface" dst_param="in_input" />
    </shader_group>"""

    return snippet


def _write_material_pbr(name, matval):
    """Compute a string in the renderer SDL for a Substance PBR material."""
    # pbr is an osl shader
    path = SHADERS_DIR.encode("unicode_escape").decode("utf-8")

    # Retrieve parameters
    basecolor_texconnect, basecolor = matval["basecolor"]
    roughness_texconnect, roughness = matval["roughness"]
    metallic_texconnect, metallic = matval["metallic"]
    specular_texconnect, specular = matval["specular"]

    # Bump/Normal
    if matval.has_bump():
        bump_texconnect, _ = matval["bump"]
    else:
        bump_texconnect = ""
    if matval.has_normal():
        normal_texconnect, _ = matval["normal"]
    else:
        normal_texconnect = ""

    # Textures and connections
    snippet_tex = matval.write_textures()
    snippet_connect = [
        basecolor_texconnect,
        roughness_texconnect,
        metallic_texconnect,
        specular_texconnect,
        bump_texconnect,
        normal_texconnect,
    ]
    snippet_connect = [s for s in snippet_connect if s]
    snippet_connect = "".join(snippet_connect)

    # Final consolidation
    snippet = f"""
        <search_path>
            {path}
        </search_path>
    <!-- Substance_PBR Shader -->
    <material name="{name}" model="osl_material">
        <parameter name="surface_shader" value="{name}_ss" />
        <parameter name="osl_surface" value="{name}_group" />
    </material>

    <surface_shader name="{name}_ss" model="physical_surface_shader" />

    <shader_group name="{name}_group">
{snippet_tex}

        <!-- Main shader -->
        <shader layer="NormalMix" type="shader" name="fc_add_normal" >
            <parameter name="in_factor" value="float 0.8" />
        </shader>
        <shader layer="MasterMix" type="shader" name="as_sbs_pbrmaterial">
            <parameter name="in_baseColor" value="color {basecolor}" />
            <parameter name="in_heightScale" value="float 1.0" />
            <parameter name="in_roughness" value="float {roughness}" />
            <parameter name="in_metallic" value="float {metallic}" />
            <parameter name="in_specularLevel" value="float {specular}" />
        </shader>
        <shader layer="Surface" type="surface" name="as_closure2surface" />
        <!-- ~Main shader -->
{snippet_connect}
        <!-- Connect normal mix to master -->
        <connect_shaders
            src_layer="NormalMix" src_param="out_normal"
            dst_layer="MasterMix" dst_param="in_normal"
        />
        <!-- Connect to surface -->
        <connect_shaders src_layer="MasterMix" src_param="out_outColor"
                         dst_layer="Surface" dst_param="in_input" />
    </shader_group>
    <!-- ~Substance_PBR Shader -->"""

    return snippet


def _write_material_passthrough(name, matval):
    """Compute a string in the renderer SDL for a passthrough material."""
    snippet = indent(matval["string"], "    ")
    return snippet.format(n=name, c=matval.default_color.to_linear())


def _write_material_fallback(name, matval):
    """Compute a string in the renderer SDL for a fallback material.

    Fallback material is a simple Diffuse material.
    """
    try:
        color = matval.material.color
        lcol = color.to_linear()
        red = float(lcol[0])
        grn = float(lcol[1])
        blu = float(lcol[2])
        assert (0 <= red <= 1) and (0 <= grn <= 1) and (0 <= blu <= 1)
    except (AttributeError, ValueError, TypeError, AssertionError):
        red, grn, blu = 1.0, 1.0, 1.0

    color = (red, grn, blu)

    snippet = (
        SNIPPET_COLOR.format(
            n=_color_name(name), c=f"{color[0]} {color[1]} {color[2]}"
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


def _write_material_emission(name, matval, write_material=True):
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet_edf = f"""
            <edf name="{name}_edf" model="diffuse_edf">
                <parameter name="radiance" value="{matval["color"][0]}" />
                <parameter name="radiance_multiplier" value="{matval["power"]}" />
                <parameter name="exposure" value="0.0" />
                <parameter name="cast_indirect_light" value="true" />
                <parameter name="importance_multiplier" value="1.0" />
                <parameter name="light_near_start" value="0.0" />
            </edf>
            <material name="{name}_mat" model="generic_material">
                <parameter name="edf" value="{name}_edf" />
                <parameter name="bump_amplitude" value="1.0" />
                <parameter name="bump_offset" value="2.0" />
                <parameter name="displacement_method" value="bump" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="alpha_map" value="1" />
                <parameter name="shade_alpha_cutouts" value="false" />
            </material>"""
    snippet_color = SNIPPET_COLOR.format(
        n=_color_name(name), c=matval["color"][1]
    )
    snippet = [snippet_color, snippet_edf]
    if write_material:
        snippet_material = _snippet_material(name, matval)
        snippet_tex = matval.write_textures()
        snippet += [snippet_tex, snippet_material]
    return "".join(snippet)

    # TODO Remove
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
        snippet_tex = matval.write_textures()
        snippet += [snippet_tex, snippet_material]
    return "".join(snippet)


MATERIALS = {
    "Passthrough": _write_material_passthrough,
    "Glass": _write_material_glass,
    "Disney": _write_material_disney,
    "Diffuse": _write_material_diffuse,
    "Mixed": _write_material_mixed,
    "Carpaint": _write_material_carpaint,
    "Substance_PBR": _write_material_pbr,
    "Emission": _write_material_emission,
}

OSL_SHADERS = ["Carpaint", "Substance_PBR"]

SNIPPET_COLOR = """
            <color name="{n}">
                <parameter name="color_space" value="linear_rgb" />
                <parameter name="multiplier" value="1.0" />
                <parameter name="wavelength_range" value="400.0 700.0" />
                <values> {c} </values>
            </color>"""

RGB = collections.namedtuple("RGB", "r g b")


def _snippet_material(name, matval):
    """Get a string for Appleseed Material entity."""
    if matval.has_displacement():
        msg = (
            f"[Material '{name}'] Warning - Appleseed "
            "does not support displacement."
        )
        _warn(msg)

    if matval.has_bump() and matval.has_normal():
        msg = (
            f"[Material '{name}'] Warning - Appleseed "
            "does not support bump and normal at the same time in a material. "
            "Falling back to bump only."
        )
        _warn(msg)

    if matval.has_bump():
        disp_method = "bump"
        disp_map = matval["bump"]
    elif matval.has_normal():
        disp_method = "normal"
        disp_map = matval["normal"]
    elif matval.shadertype == "Emission":
        return f"""
            <material name="{name}" model="generic_material">
                <parameter name="edf" value="{name}_edf" />
            </material>"""
    else:
        # No bump, no normal, no emission: return simple material
        return f"""
            <material name="{name}" model="generic_material">
                <parameter name="bsdf" value="{name}_bsdf" />
            </material>"""

    # Compute texture scale
    texobjects = matval.texobjects
    if texobjects:
        tex = next(iter(texobjects.values()))  # We take the 1st texture...
        scale = float(tex.scale) if float(tex.scale) != 0 else 1.0
    else:
        scale = 1.0
    bump_amplitude = scale

    snippet = f"""
            <material name="{name}" model="generic_material">
                <parameter name="bsdf" value="{name}_bsdf" />
                <parameter name="displacement_method" value="{disp_method}" />
                <parameter name="displacement_map" value="{disp_map}" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="bump_amplitude" value="{bump_amplitude}" />
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

    Returns:
        the name of the texture
        the SDL string of the texture
    """
    shadertype = kwargs["shadertype"]
    write_function = (
        _write_texture_osl
        if shadertype in OSL_SHADERS
        else _write_texture_internal
    )
    return write_function(**kwargs)


def _write_texture_osl(**kwargs):
    """Compute a string in renderer SDL to describe a texture in OSL format.

    The texture is computed from a property of a shader (as the texture is
    always integrated into a shader). Property's data are expected as
    arguments.

    Returns:
        the name of the texture
        the SDL string of the texture
    """
    # Retrieve parameters
    propvalue = kwargs["propvalue"]
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]

    # Compute texture name
    texname = _texname(**kwargs)

    # Retrieve texture parameters
    filename = os.path.basename(propvalue.file)
    filename = filename.encode("unicode_escape").decode("utf-8")
    scale = propvalue.scale
    translate_u = propvalue.translation_u
    translate_v = propvalue.translation_v
    rotate = propvalue.rotation

    # Bump
    if propname == "bump":
        factor = propvalue.scalar
        snippet = f"""
<!-- Bump -->
<shader layer="bumpManifold2d" type="shader" name="as_manifold2d">
    <parameter name="in_scale_frame"
               value="float[] {scale} {scale}" />
    <parameter name="in_translate_frame"
               value="float[] {translate_u} {translate_v}" />
    <parameter name="in_rotate_frame"
               value="float {rotate / 360}" />
</shader>
<shader layer="bumpTex" type="shader" name="as_texture">
    <parameter name="in_filename" value="string {filename}" />
    <parameter name="in_rgb_primaries" value="string Raw" />
    <parameter name="in_s_wrap" value="int 2" />
    <parameter name="in_t_wrap" value="int 2" />
</shader>
<shader layer="bump" type="shader" name="as_bump">
    <parameter name="in_mode" value="string Bump" />
    <parameter name="in_bump_depth" value="float {factor}" />
</shader>
<!-- ~Bump -->"""
        return texname, indent(snippet, " " * 8)

    # Normal
    if propname == "normal":
        snippet = f"""
<!-- Normal -->
<shader layer="normalManifold2d" type="shader" name="as_manifold2d">
    <parameter name="in_scale_frame"
               value="float[] {scale} {scale}" />
    <parameter name="in_translate_frame"
               value="float[] {translate_u} {translate_v}" />
    <parameter name="in_rotate_frame"
               value="float {rotate / 360}" />
</shader>
<shader layer="normalTex" type="shader" name="as_texture">
    <parameter name="in_filename"
               value="string {filename}" />
    <parameter name="in_rgb_primaries"
               value="string Raw" />
    <parameter name="in_s_wrap" value="int 2" />
    <parameter name="in_t_wrap" value="int 2" />
</shader>
<shader layer="normal" type="shader" name="as_bump">
    <parameter name="in_mode" value="string Normal Map" />
    <parameter name="in_normal_map_weight" value="float 1.0" />
    <parameter name="in_normal_map_flip_r" value="int 1" />
    <parameter name="in_normal_map_flip_g" value="int 1" />
    <parameter name="in_normal_map_swap_rg" value="int 1" />
    <parameter name="in_normal_map_coordsys" value="string Tangent Space" />
    <parameter name="in_normal_map_mode" value="string Unsigned" />
</shader>
<!-- ~Normal -->"""
        return texname, indent(snippet, " " * 8)

    # RGB
    if proptype == "RGB":
        snippet = f"""
<!-- Color texture '{propname}' -->
<shader layer="{propname}Manifold" type="shader" name="as_manifold2d">
    <parameter name="in_scale_frame"
               value="float[] {scale} {scale}" />
    <parameter name="in_translate_frame"
               value="float[] {translate_u} {translate_v}" />
    <parameter name="in_rotate_frame"
               value="float {rotate / 360}" />
</shader>
<shader layer="{propname}" type="shader" name="as_texture">
    <parameter name="in_filename" value="string {filename}" />
    <parameter name="in_enable_cms" value="int 1" />
    <parameter name="in_rgb_primaries" value="string sRGB/Rec.709" />
    <parameter name="in_s_wrap" value="int 2" />
    <parameter name="in_t_wrap" value="int 2" />
</shader>
<!-- ~Color texture '{propname}' -->"""
        return texname, indent(snippet, " " * 8)

    # Float
    if proptype == "float":
        snippet = f"""
<!-- Float texture '{propname}' -->
<shader layer="{propname}Manifold" type="shader" name="as_manifold2d">
    <parameter name="in_scale_frame"
               value="float[] {scale} {scale}" />
    <parameter name="in_translate_frame"
               value="float[] {translate_u} {translate_v}" />
    <parameter name="in_rotate_frame"
               value="float {rotate / 360}" />
</shader>
<shader layer="{propname}" type="shader" name="as_texture">
    <parameter name="in_filename"
               value="string {filename}" />
    <parameter name="in_rgb_primaries"
               value="string Raw" />
    <parameter name="in_s_wrap" value="int 2" />
    <parameter name="in_t_wrap" value="int 2" />
</shader>
<!-- ~Float texture '{propname}' -->"""
        return texname, indent(snippet, " " * 8)

    return texname, ""


def _write_texture_internal(**kwargs):
    """Compute a string in renderer SDL to describe a texture (internal).

    The texture is computed from a property of a shader (as the texture is
    always integrated into a shader). Property's data are expected as
    arguments.

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
    rotate = propvalue.rotation
    scale = propvalue.scale
    translate_u = propvalue.translation_u
    translate_v = propvalue.translation_v
    texture = f"""
        <texture name="{texname}" model="disk_texture_2d">
            <parameter name="filename" value="{filename}"/>
            <parameter name="color_space" value="{colorspace}"/>
        </texture>
        <texture_instance name="{texname}.instance" texture="{texname}">
            <parameter name="filtering_mode" value="bilinear" />
            <transform>
                <rotation axis="0.0 0.0 1.0" angle="{rotate}"/>
                <scaling value="{scale} {scale} {scale} "/>
                <translation value="{translate_u} {translate_v} 0.0"/>
            </transform>
        </texture_instance>"""

    return texname, texture


def _write_value(**kwargs):
    """Compute a string in renderer SDL from a shader property value.

    Args:
        proptype -- Shader property's type
        propvalue -- Shader property's value

    The result depends on the type of the value...
    """
    shadertype = kwargs["shadertype"]
    write_function = (
        _write_value_osl
        if shadertype in OSL_SHADERS
        else _write_value_internal
    )
    return write_function(**kwargs)


def _write_value_osl(**kwargs):
    """Compute a string in renderer SDL from a shader property value (osl).

    Args:
        proptype -- Shader property's type
        propvalue -- Shader property's value

    The result depends on the type of the value...
    """
    # Retrieve parameters
    proptype = kwargs["proptype"]
    val = kwargs["propvalue"]

    # Snippets for values
    if proptype == "RGB":
        lcol = val.to_linear()
        return ("", f"{lcol[0]:.8} {lcol[1]:.8} {lcol[2]:.8}")
    if proptype == "float":
        return ("", f"{val:.8}")

    raise NotImplementedError(proptype)


def _write_value_internal(**kwargs):
    """Compute a string in renderer SDL from a property value (internal).

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
        lcol = val.to_linear()
        value = (
            _color_name(matname),
            f"{lcol[0]:.8} {lcol[1]:.8} {lcol[2]:.8}",
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
        raise NotImplementedError(proptype)

    return value


def _write_texref(**kwargs):
    """Compute a string in SDL for a reference to a texture in a shader."""
    shadertype = kwargs["shadertype"]
    write_function = (
        _write_texref_osl
        if shadertype in OSL_SHADERS
        else _write_texref_internal
    )
    return write_function(**kwargs)


OSL_CONNECTIONS = {
    ("Carpaint", "basecolor"): [
        "in_color",
        "in_specular_color",
        "in_coating_absorption",
    ],
    ("Substance_PBR", "basecolor"): [
        "in_baseColor",
    ],
    ("Substance_PBR", "roughness"): [
        "in_roughness",
    ],
    ("Substance_PBR", "metallic"): [
        "in_metallic",
    ],
}


def _write_texref_osl(**kwargs):
    """Compute a string in SDL for a reference to a texture in a shader.

    Nota: this function assumes that main shader layer is named 'MasterMix'.
    In other cases, connections may not work properly.
    """
    shadertype = kwargs["shadertype"]
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]
    pname = propname

    # Bump
    if propname == "bump":
        # Internal connections
        texconnect = """
        <!-- Connect 'bump' -->
        <connect_shaders src_layer="bumpManifold2d" src_param="out_uvcoord"
                         dst_layer="bumpTex" dst_param="in_texture_coords" />
        <connect_shaders src_layer="bumpTex" src_param="out_channel"
                         dst_layer="bump" dst_param="in_bump_value" />
        <connect_shaders src_layer="bump" src_param="out_normal"
                         dst_layer="NormalMix" dst_param="in_normal2" />"""
        return (texconnect, "")

    # Normal
    if propname == "normal":
        # Internal connections
        texconnect = """
        <!-- Connect 'normal' -->
        <connect_shaders src_layer="normalManifold2d" src_param="out_uvcoord"
                         dst_layer="normalTex" dst_param="in_texture_coords" />
        <connect_shaders src_layer="normalTex" src_param="out_color"
                         dst_layer="normal" dst_param="in_normal_map" />
        <connect_shaders src_layer="normal" src_param="out_normal"
                         dst_layer="NormalMix" dst_param="in_normal1" />"""
        return (texconnect, "")

    inputs = OSL_CONNECTIONS[shadertype, propname]

    # RGB
    if proptype == "RGB":
        # Internal connections
        texconnect = [
            f"""
        <!-- Connect '{propname}' -->
        <connect_shaders src_layer="{pname}Manifold" src_param="out_uvcoord"
                         dst_layer="{pname}" dst_param="in_texture_coords"/>"""
        ]
        # Compute connection statement
        snippet_connect = """
        <connect_shaders src_layer="{p}" src_param="out_color"
                         dst_layer="MasterMix" dst_param="{i}" />"""
        texconnect += [snippet_connect.format(p=propname, i=i) for i in inputs]
        # Return connection statement and default value
        texconnect = "".join(texconnect)
        return (texconnect, "0.8 0.8 0.8")

    # Float
    if proptype == "float":
        # Internal connections
        texconnect = [
            f"""
        <!-- Connect '{propname}' -->
        <connect_shaders src_layer="{pname}Manifold" src_param="out_uvcoord"
                         dst_layer="{pname}" dst_param="in_texture_coords"/>"""
        ]
        # Compute connection statement
        snippet_connect = """
        <connect_shaders src_layer="{p}" src_param="out_channel"
                         dst_layer="MasterMix" dst_param="{i}" />"""
        texconnect += [snippet_connect.format(p=propname, i=i) for i in inputs]
        # Return connection statement and default value
        texconnect = "".join(texconnect)
        return (texconnect, "0.0")

    return "", ""


def _write_texref_internal(**kwargs):
    """Compute a string in SDL for a reference to a texture in a shader."""
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]

    texref = f"{_texname(**kwargs)}.instance"

    # IOR special case
    if propname == "ior":
        msg = (
            "Warning - Appleseed does not support "
            "textures for 'ior' parameter. Fallback to value 1.5"
        )
        _warn(msg)
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
#                              Test function
# ===========================================================================


def test_cmdline(batch):
    """Generate a command line for test.

    This function allows to test if renderer settings (path...) are correct
    """
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    if not batch:
        # GUI
        rpath = params.GetString("AppleseedStudioPath", "")
    else:
        # Console
        rpath = params.GetString("AppleseedCliPath", "")
    return [rpath, "--help"]


# ===========================================================================
#                              Render function
# ===========================================================================


def render(
    project,
    prefix,
    batch,
    input_file,
    output_file,
    width,
    height,
    spp,
    denoise,
):
    """Generate renderer command.

    Args:
        project -- The project to render
        prefix -- A prefix string for call (will be inserted before path to
            renderer)
        batch -- A boolean indicating whether to call UI (False) or console
            (True) version of renderer
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

    def move_elements(
        element_tag, destination, template, keep_one=False, replace=None
    ):
        """Move elements into another (root) element.

        If keep_one is set, only last element is kept.
        Replace tag by 'replace' if specified.
        """
        pattern = r"(?m)^ *<{e}(?:\s.*|)>[\s\S]*?<\/{e}>\n".format(
            e=element_tag
        )
        regex_obj = re.compile(pattern)
        contents = regex_obj.findall(template)
        contents = (
            str(contents[-1]) if contents and keep_one else "\n".join(contents)
        )
        # Replace tag if required
        if replace is not None:
            contents = contents.replace(element_tag, replace)
        template = regex_obj.sub("", template)
        pos = re.search(rf"<{destination}>\n", template).end()
        template = template[:pos] + contents + "\n" + template[pos:]
        return template

    def set_config_param(root, config, submodule, param, value):
        """Set a parameter of an submodule in a configuration.

        Submodule can be a sampler, a renderer, an engine etc.
        If submodule is None, the parameter is considered at top-level in
        configuration.
        """
        config = str(config)
        submodule = str(submodule) if submodule is not None else submodule
        param = str(param)
        value = str(value)

        config_elt = root.find(
            f"./configurations/configuration[@name='{config}']"
        )

        if submodule is not None:
            submodule_elt = config_elt.find(
                f"./parameters[@name='{submodule}']"
            )
            if not submodule_elt:
                submodule_elt = et.Element("parameters", name=submodule)
                config_elt.append(submodule_elt)
        else:
            submodule_elt = config_elt

        param_elt = submodule_elt.find(f"./parameter[@name='{param}']")
        if not param_elt:
            param_elt = et.Element("parameter", name=param)
            submodule_elt.append(param_elt)
        param_elt.set("value", value)

        return root

    # Here starts render

    # Make various adjustments on file:
    # Change image size in template, adjust camera ratio, reorganize cameras
    # declarations and specify default camera

    # Before all, open result file
    with open(input_file, "r", encoding="utf-8") as f:
        template = f.read()

    # Gather cameras, environment_edf, environment_shader, environment elements
    # in scene block (keeping only one environment element)
    template = move_elements("camera", "scene", template)
    template = move_elements("environment_edf", "scene", template)
    template = move_elements("environment_shader", "scene", template)
    template = move_elements("environment", "scene", template, True)
    template = move_elements(
        "scene_texture", "scene", template, replace="texture"
    )
    template = move_elements(
        "scene_texture_instance", "scene", template, replace="texture_instance"
    )
    template = move_elements("search_path", "search_paths", template, True)

    # Change image size
    res = re.findall(r"<parameter name=\"resolution.*?\/>", template)
    if res:
        snippet = '<parameter name="resolution" value="{} {}"/>'
        template = template.replace(res[0], snippet.format(width, height))

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

    # xml root element
    root = et.fromstring(template)

    # Set samples per pixel
    if spp:
        root = set_config_param(
            root,
            "interactive",
            "progressive_frame_renderer",
            "max_average_spp",
            spp,
        )
        root = set_config_param(
            root, "final", "uniform_pixel_renderer", "samples", spp
        )
        root = set_config_param(root, "final", None, "passes", 1)

    # Don't use Embree
    # (see https://github.com/appleseedhq/appleseed/issues/2921
    root = set_config_param(root, "interactive", None, "use_embree", 0)
    root = set_config_param(root, "final", None, "use_embree", 0)

    # Denoiser
    if denoise:
        # Nota: only final can denoise (only generic_frame_renderer, actually)
        # see code in (look for denoise):
        # https://github.com/appleseedhq/appleseed/blob/master/src/appleseed/renderer/kernel/rendering/generic/genericframerenderer.cpp
        # versus code in
        # https://github.com/appleseedhq/appleseed/blob/master/src/appleseed/renderer/kernel/rendering/progressive/progressiveframerenderer.cpp
        for frame in root.iterfind("./output/frame"):
            denoise_param = frame.find("./parameter[@name='denoiser']")
            if not denoise_param:
                denoise_param = et.Element("parameter", name="denoiser")
                frame.append(denoise_param)
            denoise_param.set("value", "on")
            tile_param = frame.find("./parameter[@name='tile_size']")
            if not tile_param:
                tile_param = et.Element("parameter", name="tile_size")
                frame.append(tile_param)
            tile_param.set("value", "32 32")
        # Use adaptive sampler for denoising
        root = set_config_param(root, "final", None, "pixel_renderer", "")
        root = set_config_param(
            root, "final", None, "tile_renderer", "adaptive"
        )

    # Template update
    template = et.tostring(root, encoding="unicode", xml_declaration=True)

    # # Beautify
    template = [l.strip(" ") for l in template.splitlines()]
    template = [l for l in template if l]  # Remove empty lines
    template = "".join(template)
    template = template.replace("<dummy>", "\n        ")
    template = template.replace("</dummy>", "")
    template = template.replace("</matrix>", "\n          </matrix>")
    with xml.dom.minidom.parseString(template) as node:
        template = node.toprettyxml(indent="  ", encoding="utf-8")

    # Write resulting output to file
    with open(input_file, "wb") as f:
        f.write(template)

    # Prepare command line parameters
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    if not batch:
        # GUI
        rpath = params.GetString("AppleseedStudioPath", "")
        args = ""
        output_file = None
    else:
        # Console
        rpath = params.GetString("AppleseedCliPath", "")
        args = params.GetString("AppleseedParameters", "")
        if args:
            args += " "
        args += f"""--output "{output_file}" """
        if spp:
            args += f"""--samples {spp} --passes 1 """
    if not rpath:
        App.Console.PrintError(
            "Unable to locate renderer executable. "
            "Please set the correct path in "
            "Edit -> Preferences -> Render\n"
        )
        return None, None
    if args:
        args += " "

    filepath = f'"{input_file}"'

    # Build Appleseed command
    cmd = prefix + rpath + " " + args + " " + filepath + "\n"

    # Return cmd, output
    # output is None in GUI mode, as no resulting image is output by Appleseed
    # in this mode...
    return cmd, output_file


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


def _warn(msg):
    """Warn user with a message."""
    fullmsg = f"[Render] [Appleseed] {msg}\n"
    App.Console.PrintWarning(fullmsg)
