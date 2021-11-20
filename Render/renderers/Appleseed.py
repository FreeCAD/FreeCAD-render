# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
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

# NOTE The coordinate system in Appleseed uses a different coordinate system.
# Y and Z are switched and Z is inverted

import os
import re
import shlex
import uuid
from tempfile import mkstemp
from math import pi, degrees, acos, atan2, sqrt
from subprocess import Popen
from textwrap import indent
import collections

import FreeCAD as App

TEMPLATE_FILTER = "Appleseed templates (appleseed_*.appleseed)"

# ===========================================================================
#                             Write functions
# ===========================================================================


def write_mesh(name, mesh, material):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""
    # Write the mesh as an OBJ tempfile
    # Known bug: mesh.Placement must be null, otherwise computation is wrong
    # due to special Appleseed coordinate system (to be fixed)
    f_handle, objfile = mkstemp(suffix=".obj", prefix="_")
    os.close(f_handle)
    tmpmesh = mesh.copy()
    tmpmesh.rotate(-pi / 2, 0, 0)
    tmpmesh.write(objfile)

    # Fix missing object name in OBJ file (mandatory in Appleseed)
    # We want to insert a 'o ...' statement before the first 'f ...'
    with open(objfile, "r", encoding="utf-8") as f:
        buffer = f.readlines()

    i = next(i for i, l in enumerate(buffer) if l.startswith("f "))
    buffer.insert(i, f"o {name}\n")

    with open(objfile, "w", encoding="utf-8") as f:
        f.write("".join(buffer))

    # Format output
    mat_name = f"{name}.{uuid.uuid1()}"  # Avoid duplicate materials
    snippet_mat = _write_material(mat_name, material)
    snippet_obj = """
            <object name="{o}" model="mesh_object">
                <parameter name="filename" value="{f}" />
            </object>
            <object_instance name="{o}.{n}.instance" object="{o}.{n}">
                <assign_material slot="default"
                                 side="front"
                                 material="{m}" />
                <assign_material slot="default"
                                 side="back"
                                 material="{m}" />
            </object_instance>"""
    snippet = snippet_mat + snippet_obj

    return snippet.format(
        n=name,
        m=mat_name,
        o=os.path.splitext(os.path.basename(objfile))[0],
        f=objfile.encode("unicode_escape").decode("utf-8"),
    )


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
            <!-- Generated by FreeCAD - Object '{n}' -->
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
            <!-- Generated by FreeCAD - Area light '{n}' -->
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
    theta = degrees(acos(vec.y / (sqrt(vec.x ** 2 + vec.y ** 2 + vec.z ** 2))))

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

            <!-- Generated by FreeCAD - Sun_sky light '{n}' -->
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


def _write_material(name, material):
    """Compute a string in the renderer SDL, to represent a material.

    This function should never fail: if the material is not recognized,
    a fallback material is provided.
    """
    try:
        snippet_mat = MATERIALS[material.shadertype](name, material)
    except KeyError:
        msg = (
            f"'{name}' - Material '{material.shadertype}' unknown by renderer,"
            " using fallback material\n"
        )
        App.Console.PrintWarning(msg)
        snippet_mat = _write_material_fallback(name, material.default_color)
    return snippet_mat


def _write_material_passthrough(name, material):
    """Compute a string in the renderer SDL for a passthrough material."""
    assert material.passthrough.renderer == "Appleseed"
    snippet = indent(material.passthrough.string, "    ")
    return snippet.format(n=name, c=material.default_color)


def _write_material_glass(name, material):
    """Compute a string in the renderer SDL for a glass material."""
    snippet_bsdf = """
            <bsdf name="{n}_bsdf" model="glass_bsdf">
                <parameter name="surface_transmittance" value="{n}_color" />
                <parameter name="ior" value="{i}" />
                <parameter name="roughness" value="0" />
                <parameter name="volume_parameterization"
                           value="transmittance" />
            </bsdf>"""
    snippet = SNIPPET_COLOR + snippet_bsdf + SNIPPET_MATERIAL
    return snippet.format(n=name, c=material.glass.color, i=material.glass.ior)


def _write_material_disney(name, material):
    """Compute a string in the renderer SDL for a Disney material."""
    snippet_bsdf = """
            <bsdf name="{n}_bsdf" model="disney_brdf">
                <parameter name="base_color" value="{n}_color" />
                <parameter name="subsurface" value="{sb}" />
                <parameter name="metallic" value="{m}" />
                <parameter name="specular" value="{sp}" />
                <parameter name="specular_tint" value="{spt}" />
                <parameter name="roughness" value="{r}" />
                <parameter name="anisotropic" value="{a}" />
                <parameter name="sheen" value="{sh}" />
                <parameter name="sheen_tint" value="{sht}" />
                <parameter name="clearcoat" value="{cc}" />
                <parameter name="clearcoat_gloss" value="{ccg}" />
            </bsdf>"""
    snippet = SNIPPET_COLOR + snippet_bsdf + SNIPPET_MATERIAL
    return snippet.format(
        n=name,
        c=material.disney.basecolor,
        sb=material.disney.subsurface,
        m=material.disney.metallic,
        sp=material.disney.specular,
        spt=material.disney.speculartint,
        r=material.disney.roughness,
        a=material.disney.anisotropic,
        sh=material.disney.sheen,
        sht=material.disney.sheentint,
        cc=material.disney.clearcoat,
        ccg=material.disney.clearcoatgloss,
    )


def _write_material_diffuse(name, material):
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet_bsdf = """
            <bsdf name="{n}_bsdf" model="lambertian_brdf">
                <parameter name="reflectance" value="{n}_color" />
            </bsdf>"""
    snippet = SNIPPET_COLOR + snippet_bsdf + SNIPPET_MATERIAL
    return snippet.format(n=name, c=material.diffuse.color)


def _write_material_mixed(name, material):
    """Compute a string in the renderer SDL for a Mixed material."""
    snippet_g = _write_material_glass(f"{name}_glass", material.mixed)
    snippet_d = _write_material_diffuse(f"{name}_diffuse", material.mixed)
    snippet_mixed = """
            <bsdf name="{n}_bsdf" model="bsdf_blend">
                <parameter name="bsdf0" value="{n}_glass_bsdf" />
                <parameter name="bsdf1" value="{n}_diffuse_bsdf" />
                <parameter name="weight" value="{r}" />
            </bsdf>"""
    snippet = snippet_g + snippet_d + snippet_mixed + SNIPPET_MATERIAL
    return snippet.format(n=name, r=material.mixed.transparency)

# Multilayer OSL shader
# http://vadrouillegraphique.blogspot.com/2013/06/pyla-13-faster-than-base-material.html
# http://pressf9.free.fr/compounds/Pyla1.3.osl
PYLA13 = """
/*
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 */

/* PYLA 1.3 : PhYsically Correct LAyer Mixer
 *
 * by François GASTALDO
 *
 * Contact me at: pressf9@free.fr
 *
 * Blog (3D, shaders, photos and more) : http://vadrouillegraphique.blogspot.fr/
 *
 * Small Documentation :
 * This shader is a Physically correct Shader Mixer for layered Materials.
 *
 * It simulates materials made of multiple coating, or layers, like car paint,
 * polished nails...
 *
 * This is a very simple shader, but very powerful!
 *
 * You could better manage your mixed Materials, in more realistic way, and
 * with better results.
 *
 * Documentation:
 * INPUT:
 *  Base = the base shader, the layer will come on top of it.
 *
 *  Layer = The layer Material.
 *          You can use any shader, except tranparent or glass shader.
 *          Pyla is a mixer, and not a real layer simulation, so tranparent
 *          shader should give unwanted results !
 *
 *  Opacity = Between 0.0 and 1.0,  0.0 = no visible layer, 1.0 = full
 *            effect.
 *
 *  Depth = The depth of the layer.
 * 	        The thicker the layer is, the less you could see the base.
 *          Value between 0.0 to 10.0, good value : 2.0.
 *
 *  Fresnel = Fresnel visibility for the layer. A full fresnel (1.0)
 *            is perfect for clear coat simulation.
 *            0.0 = the depth only control the visibilty, and not the fresnel
 *            effect.
 *
 *  IoR = The Index of Refraction for the fresnel effect.
 *        The greater it is, the more visible the layer is.
 *
 *  MaskLayer = Put here a mask image to have the layer visible just on
 *              the white part of the mask.
 *
 *  Secondary_Layer = Secondary Optimization:
 *  	              0.0 = NO Optimization.
 *                    1.0 = Secondary is Base, use this if your
 *                          Base shader is faster than Layer Shader.
 *  	              2.0 = Secondary is Layer,  use this if your
 *                          Layer shader is faster than Base Shader.
 *  	              3.0 = Secondary is black (null closure).
 *                          This is the fatest render, but could be unwanted
 *                          in case of readable reflection of the object.
 *
 * OUTPUT :
 *  Layered (Closure) = Mixed Base and Layer Inputs.
 *
 *  Layer Mix (float) = Amount of mixing between the Base and Layer.
 *                      You can use it to put in a classical Shader Mixer,
 *                      or a color mixier, as you wish!
 *
 *
 * TODO :
 *  Transparent Layer capability.
 *
 * This shader was edited with Sublime text Editor: http://www.sublimetext.com/
 * with OSL package: https://github.com/roesti77/Sublime-Open-Shading-Language
 *
 * This shader is made for educational purpose only. Use it in production at
 * your own risk.
 *
 * Closures are for Blender/Cycles. They could need adaptation for your
 * renderer.
 *
 * If you use this shader, please credit it and me. Thank you.
 *
 * Enjoy!
 *
 * François Gastaldo
 *
 */

float fresnel_dielectric(vector Incoming, normal Normal, float eta)
{{
  // Compute fresnel reflectance without explicitly computing
  // the refracted direction
  float c = fabs(dot(Incoming, Normal));
  float g = eta * eta - 1 + c * c;
  float result;

  if (g > 0) {{
    g = sqrt(g);
    float A = (g - c) / (g + c);
    float B = (c * (g + c) - 1) / (c * (g - c) + 1);
    result = 0.5 * A * A * (1 + B * B);
  }} else {{
    result = 1.0;  // TIR (no refracted component)
  }}

  return result;
}}

shader PyLa(
  closure color Base = diffuse(N),
  closure color Layer = 0.0,
  float Opacity = 0.5,
  float depth = 2.0,
  float Fresnel = 0.5,
  float IoR = 1.5,
  float MaskLayer = 1.0,
  float Secondary_Layer = 1.0,

  output closure color Layered = diffuse(N),
  output float layermix = 0.5
)
{{
  // version 1.2, with optimization
  float Optim_Secondary = Secondary_Layer;

  int RTdirect = raytype("camera");

  int Optimise = (RTdirect) | (Optim_Secondary == 0.0);

  if (Optimise)
  {{
    // Incidence with depth power
    float InvDepth = 1.0 / max(depth, 0.01);
    float incidence = pow((1.0 - dot(I, N)), InvDepth);
    float fresnelincidence = pow(fresnel_dielectric(I, N, IoR), InvDepth);

    // Mix factor
    float MixLayer = clamp(
      MaskLayer * Opacity * ((Fresnel * fresnelincidence) + (1.0 - Fresnel) * incidence),
      0.0,
      1.0
    );
    layermix = MixLayer;
  }} else {{
    if (Secondary_Layer == 1.0)
    {{
      Layered = Base;
    }} else {{
      if (Secondary_Layer == 3.0)
      {{
        Layered = 0.0;
      }} else {{
        Layered = Layer;
      }}
    }}
  }}
}}
"""

def _write_material_carpaint(name, material):
    """Compute a string in the renderer SDL for a carpaint material."""
    snippet = """
    <!-- Generated by FreeCAD - Carpaint Shader -->
    <material name="{n}" model="osl_material">
        <parameter name="osl_surface" value="{n}_group" />
        <parameter name="surface_shader" value="{n}_ss" />
    </material>
    <surface_shader name="{n}_ss" model="physical_surface_shader" />
    <shader_group name="{n}_group">
        <shader type="shader" name="{n}_osl" layer="source_code1">
             <osl_code>
{o}
             </osl_code>
        </shader>
        <shader type="surface" name="as_closure2surface" layer="surface">
            <osl_code>
surface as_closure2surface
[[
    string as_node_name = "asClosure2Surface",
    string as_category = "surface"
]]
(
    closure color in_input = 0
    [[
        string label = "Input"
    ]]
)
{{{{
    Ci = in_input;
}}}}
            </osl_code>
        </shader>
        <connect_shaders src_layer="source_code1"
                         src_param="Layered"
                         dst_layer="surface"
                         dst_param="in_input" />
    </shader_group>
    """
    return snippet.format(n=name, o=PYLA13)



def _write_material_fallback(name, material):
    """Compute a string in the renderer SDL for a fallback material.

    Fallback material is a simple Diffuse material.
    """
    try:
        red = float(material.color.r)
        grn = float(material.color.g)
        blu = float(material.color.b)
        assert (0 <= red <= 1) and (0 <= grn <= 1) and (0 <= blu <= 1)
    except (AttributeError, ValueError, TypeError, AssertionError):
        red, grn, blu = 1, 1, 1
    finally:
        color = RGB(red, grn, blu)
    snippet = (
        SNIPPET_COLOR
        + """
            <!-- Generated by FreeCAD - Object '{n}' - FALLBACK -->
            <bsdf name="{n}_bsdf" model="lambertian_brdf">
                <parameter name="reflectance" value="{n}_color" />
            </bsdf>"""
        + SNIPPET_MATERIAL
    )
    return snippet.format(n=name, c=color)


MATERIALS = {
    "Passthrough": _write_material_passthrough,
    "Glass": _write_material_glass,
    "Disney": _write_material_disney,
    "Diffuse": _write_material_diffuse,
    "Mixed": _write_material_mixed,
    "Carpaint": _write_material_carpaint,
}

SNIPPET_COLOR = """
            <!-- Generated by FreeCAD - Color '{n}_color' -->
            <color name="{n}_color">
                <parameter name="color_space" value="srgb" />
                <parameter name="multiplier" value="1.0" />
                <parameter name="wavelength_range" value="400.0 700.0" />
                <values> {c.r} {c.g} {c.b} </values>
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


# ===========================================================================
#                              Render function
# ===========================================================================


def render(project, prefix, external, output, width, height):
    """Run renderer.

    Args:
        project -- The project to render
        prefix -- A prefix string for call (will be inserted before path to
            renderer)
        external -- A boolean indicating whether to call UI (true) or console
            (false) version of renderder
        width -- Rendered image width, in pixels
        height -- Rendered image height, in pixels

    Returns:
        A path to output image file
    """

    def move_elements(element_tag, destination, template, keep_one=False):
        """Move elements into another (root) element.

        If keep_one is set, only last element is kept.
        """
        pattern = r"(?m)^ *<{e}\s.*>[\s\S]*?<\/{e}>\n".format(e=element_tag)
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
    App.ActiveDocument.recompute()

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
        return ""
    if args:
        args += " "

    filepath = f'"{project.PageResult}"'

    # Call Appleseed (asynchronously)
    cmd = prefix + rpath + " " + args + " " + filepath + "\n"
    App.Console.PrintMessage(cmd)
    try:
        Popen(shlex.split(cmd))
    except OSError as err:
        msg = "Appleseed call failed: '" + err.strerror + "'\n"
        App.Console.PrintError(msg)

    return output if not external else None


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
