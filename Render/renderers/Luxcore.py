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

"""LuxCore renderer plugin for FreeCAD Render workbench."""

# Suggested links to renderer documentation:
# https://wiki.luxcorerender.org/LuxCore_SDL_Reference_Manual_v2.6
# https://github.com/LuxCoreRender/LuxCore/blob/master/scenes/displacement/displacement.scn

import os
from textwrap import dedent
import configparser

import FreeCAD as App

from .utils.misc import fovy_to_fovx

TEMPLATE_FILTER = "Luxcore templates (luxcore_*.cfg)"

# ===========================================================================
#                             Write functions
# ===========================================================================


def write_mesh(name, mesh, material, **kwargs):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""
    # Material values
    matval = material.get_material_values(
        name, _write_texture, _write_value, _write_texref
    )

    # Compute bump & normal statements
    #
    # Nota: Luxcore does not support both bump and normal at the same time
    # (bumptex excludes normaltex...)
    # Hence we have to combine them before and connect the result to bumptex
    # only, like in
    # https://github.com/LuxCoreRender/LuxCore/blob/master/scenes/bump/bump-add.scn
    snippet_mat = _write_material(name, matval)
    snippet_tex = matval.write_textures()
    if matval.has_bump() and matval.has_normal():
        snippet_bump = f"""\
scene.textures.{name}_bump.type = mix
scene.textures.{name}_bump.amount = 0.9
scene.textures.{name}_bump.texture1 = {matval["bump"]}
scene.textures.{name}_bump.texture2 = {matval["normal"]}
scene.materials.{name}.bumptex = {name}_bump
"""
    elif matval.has_bump():  # and not matval.has_normal()...
        snippet_bump = f"""\
scene.materials.{name}.bumptex = {matval["bump"]}
"""
    elif matval.has_normal():  # and not matval.has_bump()...
        snippet_bump = f"""\
scene.materials.{name}.bumptex = {matval["normal"]}
"""
    else:
        snippet_bump = ""

    # Displacement (if any)
    if matval.has_displacement():
        obj_shape = f"{name}_disp"
        snippet_disp = f"""
scene.shapes.{name}_disp.type = displacement
scene.shapes.{name}_disp.source = {name}_mesh
scene.shapes.{name}_disp.scale = 1
scene.shapes.{name}_disp.map = {matval["displacement"]}
scene.shapes.{name}_disp.map.type = vector
# Mudbox channel order
scene.shapes.{name}_disp.map.channels = 0 2 1
"""
    else:
        obj_shape = f"{name}_mesh"
        snippet_disp = ""

    # Get PLY file
    plyfile = mesh.write_file(name, mesh.ExportType.PLY)

    # Transformation matrix
    trans = (
        " ".join(str(v) for v in col)
        for col in mesh.transformation.get_matrix_columns()
    )
    trans = "  ".join(trans)

    # Object & Mesh
    snippet_obj = f"""
# Object '{name}'
scene.objects.{name}.shape = {obj_shape}
scene.objects.{name}.material = {name}
scene.objects.{name}.transformation = {trans}
scene.shapes.{name}_mesh.type = mesh
scene.shapes.{name}_mesh.ply = "{plyfile}"
"""
    # Consolidation
    snippet = [
        snippet_obj,
        snippet_disp,
        snippet_mat,
        snippet_tex,
        snippet_bump,
    ]
    snippet = (s for s in snippet if s)
    snippet = "\n".join(snippet)

    return snippet


def write_camera(name, pos, updir, target, fov, resolution, **kwargs):
    """Compute a string in renderer SDL to represent a camera."""
    # The Luxcore fov is in the largest image dimension, so for the typical
    # case where the image width is larger than the height the vertical fov
    # used by FreeCAD needs to be converted to a horizontal fov
    orig = pos.Base
    if resolution[0] > resolution[1]:  # aspect ratio > 1
        fov = fovy_to_fovx(fov, *resolution)

    snippet = f"""
# Camera '{name}'
scene.camera.lookat.orig = {orig.x} {orig.y} {orig.z}
scene.camera.lookat.target = {target.x} {target.y} {target.z}
scene.camera.up = {updir.x} {updir.y} {updir.z}
scene.camera.fieldofview = {fov}
"""
    return snippet


def write_pointlight(name, pos, color, power):
    """Compute a string in renderer SDL to represent a point light."""
    # From LuxCore doc:
    # power is in watts
    # efficiency is in lumens/watt
    efficiency = 15  # incandescent light bulb ratio (average)
    gain = 10  # Guesstimated! (don't hesitate to propose more sensible values)

    snippet = """
# Point light '{n}'
scene.lights.{n}.type = point
scene.lights.{n}.position = {o.x} {o.y} {o.z}
scene.lights.{n}.color = {c[0]} {c[1]} {c[2]}
scene.lights.{n}.power = {p}
scene.lights.{n}.gain = {g} {g} {g}
scene.lights.{n}.efficency = {e}
"""
    return dedent(snippet).format(
        n=name, o=pos, c=color, p=power, g=gain, e=efficiency
    )


def write_arealight(
    name, pos, size_u, size_v, color, power, transparent, **kwargs
):
    """Compute a string in renderer SDL to represent an area light."""
    efficiency = 15
    gain = 0.001  # Guesstimated!

    # We have to transpose 'pos' to make it fit for Lux
    # As 'transpose' method is in-place, we first make a copy
    placement = App.Matrix(pos.toMatrix())
    placement.transpose()
    trans = " ".join([str(a) for a in placement.A])

    snippet = """
# Area light '{n}'
scene.materials.{n}.type = matte
scene.materials.{n}.emission = {c[0]} {c[1]} {c[2]}
scene.materials.{n}.emission.gain = {g} {g} {g}
scene.materials.{n}.emission.power = {p}
scene.materials.{n}.emission.efficency = {e}
scene.materials.{n}.transparency = {a}
scene.materials.{n}.kd = 0.0 0.0 0.0
scene.objects.{n}.type = inlinedmesh
scene.objects.{n}.vertices = -{u} -{v} 0 {u} -{v} 0 {u} {v} 0 -{u} {v} 0
scene.objects.{n}.faces = 0 1 2 0 2 3 0 2 1 0 3 2
scene.objects.{n}.material = {n}
scene.objects.{n}.transformation = {t}
"""
    # Note: area light is made double-sided (consistency with other renderers)

    return dedent(snippet).format(
        n=name,
        t=trans,
        c=color,
        p=power,
        e=efficiency,
        g=gain,
        u=size_u / 2,
        v=size_v / 2,
        a=0 if transparent else 1,
    )


def write_sunskylight(name, direction, distance, turbidity, albedo, **kwargs):
    """Compute a string in renderer SDL to represent a sunsky light."""
    gain_preset = kwargs.get("GainPreset", "Mitigated")
    if gain_preset == "Physical":
        gain = 1.0
    elif gain_preset == "Mitigated":
        gain = 0.00003
    elif gain_preset == "Custom":
        gain = kwargs.get("CustomGain")
    else:
        raise NotImplementedError(gain_preset)
    snippet = f"""
# Sunsky light '{name}'
scene.lights.{name}_sun.type = sun
scene.lights.{name}_sun.turbidity = {turbidity}
scene.lights.{name}_sun.dir = {direction.x} {direction.y} {direction.z}
scene.lights.{name}_sky.type = sky2
scene.lights.{name}_sky.turbidity = {turbidity}
scene.lights.{name}_sky.dir = {direction.x} {direction.y} {direction.z}
scene.lights.{name}_sky.groundalbedo = {albedo} {albedo} {albedo}
scene.lights.{name}_sun.gain = {gain} {gain} {gain}
scene.lights.{name}_sky.gain = {gain} {gain} {gain}
"""
    return snippet


def write_imagelight(name, image, **kwargs):
    """Compute a string in renderer SDL to represent an image-based light."""
    snippet = """
# Image light '{n}'
scene.lights.{n}.type = infinite
scene.lights.{n}.transformation = -1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1
scene.lights.{n}.file = "{f}"
"""
    return dedent(snippet).format(n=name, f=image)


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
        snippet_mat = _write_material_fallback(name, matval.default_color)
    else:
        snippet_mat = write_function(name, matval)
    return snippet_mat


def _write_material_passthrough(name, matval):
    """Compute a string in the renderer SDL for a passthrough material."""
    # snippet = indent(matval["string"], "    ")
    snippet = matval["string"]
    return snippet.format(n=name, c=matval.default_color)


def _write_material_glass(name, matval):
    """Compute a string in the renderer SDL for a glass material."""
    return f"""
scene.materials.{name}.type = glass
scene.materials.{name}.kt = {matval["color"]}
scene.materials.{name}.interiorior = {matval["ior"]}
"""


def _write_material_disney(name, matval):
    """Compute a string in the renderer SDL for a Disney material."""
    return f"""
scene.materials.{name}.type = disney
scene.materials.{name}.basecolor = {matval["basecolor"]}
scene.materials.{name}.subsurface = {matval["subsurface"]}
scene.materials.{name}.metallic = {matval["metallic"]}
scene.materials.{name}.specular = {matval["specular"]}
scene.materials.{name}.speculartint = {matval["speculartint"]}
scene.materials.{name}.roughness = {matval["roughness"]}
scene.materials.{name}.anisotropic = {matval["anisotropic"]}
scene.materials.{name}.sheen = {matval["sheen"]}
scene.materials.{name}.sheentint = {matval["sheentint"]}
scene.materials.{name}.clearcoat = {matval["clearcoat"]}
scene.materials.{name}.clearcoatgloss = {matval["clearcoatgloss"]}
"""


def _write_material_pbr(name, matval):
    """Compute a string in the renderer SDL for a Substance PBR material."""
    return f"""
scene.materials.{name}.type = disney
scene.materials.{name}.basecolor = {matval["basecolor"]}
scene.materials.{name}.roughness = {matval["roughness"]}
scene.materials.{name}.metallic = {matval["metallic"]}
scene.materials.{name}.specular = {matval["specular"]}
"""


def _write_material_diffuse(name, matval):
    """Compute a string in the renderer SDL for a Diffuse material."""
    return f"""
scene.materials.{name}.type = matte
scene.materials.{name}.kd = {matval["color"]}
"""


def _write_material_mixed(name, matval):
    """Compute a string in the renderer SDL for a Mixed material."""
    # Glass
    submat_g = matval.getmixedsubmat("glass")
    snippet_g = _write_material_glass(f"{name}_glass", submat_g)
    snippet_g_tex = submat_g.write_textures()

    # Diffuse
    submat_d = matval.getmixedsubmat("diffuse")
    snippet_d = _write_material_diffuse(f"{name}_diffuse", submat_d)
    snippet_d_tex = submat_d.write_textures()

    # Mix
    snippet_m = f"""
scene.materials.{name}.type = mix
scene.materials.{name}.material1 = {name}_diffuse
scene.materials.{name}.material2 = {name}_glass
scene.materials.{name}.amount = {matval["transparency"]}
"""
    return snippet_g + snippet_d + snippet_g_tex + snippet_d_tex + snippet_m


def _write_material_carpaint(name, matval):
    """Compute a string in the renderer SDL for a carpaint material."""
    return f"""
scene.materials.{name}.type = carpaint
scene.materials.{name}.kd = {matval["basecolor"]}
"""


def _write_material_fallback(name, matval):
    """Compute a string in the renderer SDL for a fallback material.

    Fallback material is a simple Diffuse material.
    """
    try:
        red = float(matval.default_color.r)
        grn = float(matval.default_color.g)
        blu = float(matval.default_color.b)
        assert (0 <= red <= 1) and (0 <= grn <= 1) and (0 <= blu <= 1)
    except (AttributeError, ValueError, TypeError, AssertionError):
        red, grn, blu = 1, 1, 1
    snippet = """
scene.materials.{n}.type = matte
scene.materials.{n}.kd = {r} {g} {b}
"""
    return snippet.format(n=name, r=red, g=grn, b=blu)


MATERIALS = {
    "Passthrough": _write_material_passthrough,
    "Glass": _write_material_glass,
    "Disney": _write_material_disney,
    "Diffuse": _write_material_diffuse,
    "Mixed": _write_material_mixed,
    "Carpaint": _write_material_carpaint,
    "Substance_PBR": _write_material_pbr,
}

# ===========================================================================
#                           Texture management
# ===========================================================================


def _write_texture(**kwargs):
    """Compute a string in renderer SDL to describe a texture.

    The texture is computed from a property of a shader (as the texture is
    always integrated into a shader). Property's data are expected as
    arguments.

    Args:
        objname -- Object name for which the texture is computed
        propname -- Name of the shader property
        proptype -- Type of the shader property
        propvalue -- Value of the shader property

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
    texname = f"{objname}_{propvalue.name}_{propvalue.subname}"
    gamma = 2.2 if proptype == "RGB" else 1.0
    filename = propvalue.file
    rotation = float(propvalue.rotation)
    scale = 1 / float(propvalue.scale)
    trans_u = float(propvalue.translation_u)
    trans_v = float(propvalue.translation_v)

    # Expand texture into SDL
    # 3 cases: bump, normal or plain (default)
    if propname == "bump":
        # Bump texture
        factor = propvalue.scalar if propvalue.scalar is not None else 1.0
        snippet = f"""
scene.textures.{texname}_img.type = imagemap
scene.textures.{texname}_img.file = "{filename}"
scene.textures.{texname}_img.gamma = {gamma}
scene.textures.{texname}_img.mapping.type = uvmapping2d
scene.textures.{texname}_img.mapping.rotation = {rotation}
scene.textures.{texname}_img.mapping.uvscale = {scale} {scale}
scene.textures.{texname}_img.mapping.uvdelta = {trans_u} {trans_v}
scene.textures.{texname}.type = scale
scene.textures.{texname}.texture1 = {factor}
scene.textures.{texname}.texture2 = {texname}_img
"""
    elif propname == "normal":
        # Normal texture
        factor = propvalue.scalar if propvalue.scalar is not None else 1.0
        snippet = f"""
scene.textures.{texname}_img.type = imagemap
scene.textures.{texname}_img.file = "{filename}"
scene.textures.{texname}_img.gamma = {gamma}
scene.textures.{texname}_img.channel = "rgb"
scene.textures.{texname}_img.mapping.type = uvmapping2d
scene.textures.{texname}_img.mapping.rotation = {rotation}
scene.textures.{texname}_img.mapping.uvscale = {scale} {scale}
scene.textures.{texname}_img.mapping.uvdelta = {trans_u} {trans_v}
scene.textures.{texname}.type = normalmap
scene.textures.{texname}.texture = {texname}_img
scene.textures.{texname}.scale = {factor}
"""
    else:
        # Plain texture
        snippet = f"""
scene.textures.{texname}.type = imagemap
scene.textures.{texname}.file = "{filename}"
scene.textures.{texname}.gamma = {gamma}
scene.textures.{texname}.mapping.type = uvmapping2d
scene.textures.{texname}.mapping.rotation = {rotation}
scene.textures.{texname}.mapping.uvscale = {scale} {scale}
scene.textures.{texname}.mapping.uvdelta = {trans_u} {trans_v}
"""

    return texname, snippet


VALSNIPPETS = {
    "RGB": "{val.r} {val.g} {val.b}",
    "float": "{val}",
    "node": "",
    "RGBA": "{val.r} {val.g} {val.b} {val.a}",
    "texonly": "{val}",
    "str": "{val}",
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

    # Snippets for values
    snippet = VALSNIPPETS[proptype]
    value = snippet.format(val=propvalue)
    return value


def _write_texref(**kwargs):
    """Compute a string in SDL for a reference to a texture in a shader."""
    texname = kwargs["texname"]
    return texname


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
        batch -- A boolean indicating whether to call console (True) or
            UI (False) version of renderer
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

    def export_section(section, prefix, suffix):
        """Export a section to a temporary file."""
        f_path = os.path.join(export_dir, f"{prefix}.{suffix}")
        result = [f"{k} = {v}" for k, v in dict(section).items()]
        with open(f_path, "w", encoding="utf-8") as output:
            output.write("\n".join(result))
        return f_path

    # LuxCore requires 2 files:
    # - a configuration file, with rendering parameters (engine, sampler...)
    # - a scene file, with the scene objects (camera, lights, meshes...)
    # So we have to generate both...

    # Get export directory
    export_dir = os.path.dirname(input_file)

    # Get page result content (ie what the calling module baked for us)
    pageresult = configparser.ConfigParser(strict=False)  # Allow dupl. keys
    pageresult.optionxform = lambda option: option  # Case sensitive keys
    pageresult.read(input_file)

    # Compute output
    output = (
        output_file
        if output_file
        else os.path.splitext(input_file)[0] + ".png"
    )

    # Complete configuration
    config = pageresult["Configuration"]

    # General settings
    config["renderengine.seed"] = "1"
    config["film.width"] = str(width)
    config["film.height"] = str(height)
    config["periodicsave.film.outputs.period"] = "1" if not batch else "-1"
    config["resumerendering.filesafe"] = "0"
    if spp > 0:
        config["batch.haltspp"] = str(spp)
    elif batch:
        # In case of batch mode and spp==0, we force to an arbitrary value
        # Otherwise, Luxcore will run forever
        config["batch.haltspp"] = str(32)
    if denoise:
        # If denoiser is invoked, must be in "Image view",
        # otherwise the result is not consistent...
        config["screen.tool.type"] = "IMAGE_VIEW"

    # config["context.verbose"] = "1"
    # config["screen.refresh.interval"] = "10000"  # milliseconds...
    # config["path.aovs.warmup.spp"] = "2000"

    # Pipelines
    config["film.imagepipelines.0.0.type"] = "NOP"
    if denoise:
        config["film.imagepipelines.0.1.type"] = "INTEL_OIDN"
        config["film.imagepipelines.0.1.prefilter.enable"] = "1"
    config["film.imagepipelines.0.99.type"] = "GAMMA_CORRECTION"
    config["film.imagepipelines.0.99.gamma"] = "2.2"
    config["film.imagepipelines.1.0.type"] = "NOP"

    if denoise:
        # Denoiser triggering is driven by those settings
        # (at least in batch mode)
        config["film.noiseestimation.warmup"] = str(spp)
        config["film.noiseestimation.index"] = "1"

    # Outputs
    config["film.outputs.0.type"] = "RGB_IMAGEPIPELINE"
    config["film.outputs.0.filename"] = output
    config["film.outputs.0.index"] = "0"
    if denoise:
        config["film.outputs.1.type"] = "ALBEDO"
        config["film.outputs.1.filename"] = output + "_ALBEDO.exr"
        config["film.outputs.2.type"] = "AVG_SHADING_NORMAL"
        config["film.outputs.2.filename"] = output + "_AVG_SHADING_NORMAL.exr"

    cfg_path = export_section(config, project.Name, "cfg")

    # Export scene
    scene = pageresult["Scene"]
    scn_path = export_section(scene, project.Name, "scn")

    # Get rendering parameters
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    args = params.GetString("LuxCoreParameters", "")
    rpath = params.GetString(
        "LuxCorePath" if not batch else "LuxCoreConsolePath", ""
    )
    if not rpath:
        msg = (
            "Unable to locate renderer executable. Please set the correct "
            "path in Edit -> Preferences -> Render\n"
        )
        App.Console.PrintError(msg)
        return None, None

    # Prepare command line and return
    cmd = f"""{prefix}{rpath} {args} -o "{cfg_path}" -f "{scn_path}"\n"""

    return cmd, output
