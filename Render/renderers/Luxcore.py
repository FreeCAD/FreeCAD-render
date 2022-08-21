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
from tempfile import mkstemp
from textwrap import dedent
import configparser

import FreeCAD as App

TEMPLATE_FILTER = "Luxcore templates (luxcore_*.cfg)"

# ===========================================================================
#                             Write functions
# ===========================================================================


def write_mesh(name, mesh, material):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""
    # Material values
    materialvalues = material.get_material_values(
        name, _write_texture, _write_value, _write_texref
    )

    # Compute material, texture, bump & normal statements
    snippet_mat = _write_material(name, materialvalues)
    snippet_tex = materialvalues.write_textures()
    snippet_bump = (
        f"""scene.materials.{name}.bumptex = {materialvalues["bump"]}\n"""
        if materialvalues.has_bump()
        else ""
    )
    snippet_normal = (
        f"""scene.materials.{name}.normaltex = {materialvalues["normal"]}\n"""
        if materialvalues.has_normal()
        else ""
    )

    # Points and vertices
    topology = mesh.Topology  # Compute once
    points = [f"{v.x} {v.y} {v.z}" for v in topology[0]]
    points = " ".join(points)
    tris = [f"{t[0]} {t[1]} {t[2]}" for t in topology[1]]
    tris = " ".join(tris)

    # UV map
    if mesh.has_uvmap():
        uvs = [f"{t.x} {t.y}" for t in mesh.uvmap]
        uvs = " ".join(uvs)
        snippet_uv = f"""scene.shapes.{name}_mesh.uvs = {uvs}\n"""
    else:
        snippet_uv = ""

    # Displacement (if any)
    if materialvalues.has_displacement():
        obj_shape = f"{name}_disp"
        snippet_disp = f"""
scene.shapes.{name}_disp.type = displacement
scene.shapes.{name}_disp.source = {name}_mesh
scene.shapes.{name}_disp.scale = 1
scene.shapes.{name}_disp.map = {materialvalues["displacement"]}
scene.shapes.{name}_disp.map.type = vector
# Mudbox channel order
scene.shapes.{name}_disp.map.channels = 0 2 1
"""
    else:
        obj_shape = f"{name}_mesh"
        snippet_disp = ""

    # Object & Mesh
    snippet_obj = f"""
# Object '{name}'
scene.objects.{name}.shape = {obj_shape}
scene.objects.{name}.material = {name}
scene.shapes.{name}_mesh.type = inlinedmesh
scene.shapes.{name}_mesh.vertices = {points}
scene.shapes.{name}_mesh.faces = {tris}
"""

    # Consolidation
    snippet = (
        snippet_obj
        + snippet_disp
        + snippet_uv
        + snippet_mat
        + snippet_bump
        + snippet_normal
        + snippet_tex
    )
    return dedent(snippet)


def write_camera(name, pos, updir, target, fov):
    """Compute a string in renderer SDL to represent a camera."""
    snippet = """
# Camera '{n}'
scene.camera.lookat.orig = {o.x} {o.y} {o.z}
scene.camera.lookat.target = {t.x} {t.y} {t.z}
scene.camera.up = {u.x} {u.y} {u.z}
scene.camera.fieldofview = {f}
"""
    return dedent(snippet).format(n=name, o=pos.Base, t=target, u=updir, f=fov)


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


def write_arealight(name, pos, size_u, size_v, color, power, transparent):
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


def write_sunskylight(name, direction, distance, turbidity, albedo):
    """Compute a string in renderer SDL to represent a sunsky light."""
    snippet = """
# Sunsky light '{n}'
scene.lights.{n}_sun.type = sun
scene.lights.{n}_sun.turbidity = {t}
scene.lights.{n}_sun.dir = {d.x} {d.y} {d.z}
scene.lights.{n}_sky.type = sky2
scene.lights.{n}_sky.turbidity = {t}
scene.lights.{n}_sky.dir = {d.x} {d.y} {d.z}
scene.lights.{n}_sky.groundalbedo = {g} {g} {g}
"""
    return dedent(snippet).format(n=name, t=turbidity, d=direction, g=albedo)


def write_imagelight(name, image):
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

# TODO Fix normals issue (see Gauge test file, with mirror)


def _write_material(name, material):
    """Compute a string in the renderer SDL, to represent a material.

    This function should never fail: if the material is not recognized,
    a fallback material is provided.
    """
    try:
        write_function = MATERIALS[material.shadertype]
    except KeyError:
        msg = (
            "'{}' - Material '{}' unknown by renderer, using fallback "
            "material\n"
        )
        App.Console.PrintWarning(msg.format(name, material.shadertype))
        snippet_mat = _write_material_fallback(name, material.default_color)
    else:
        snippet_mat = write_function(name, material)
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
}

# ===========================================================================
#                           Texture management
# ===========================================================================


def _write_texture(objname, propname, proptype, propvalue):
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
    # Compute texture name
    texname = f"{objname}_{propvalue.name}_{propvalue.subname}"

    # Compute gamma
    gamma = 2.2 if proptype == "RGB" else 1.0

    # Expand texture into SDL
    # 3 cases: bump, normal or plain (default)
    if propname == "bump":
        # Bump texture
        snippet = """
scene.textures.{n}_bump.type = imagemap
scene.textures.{n}_bump.file = "{f}"
scene.textures.{n}_bump.gamma = {g}
scene.textures.{n}_bump.mapping.type = uvmapping2d
scene.textures.{n}_bump.mapping.rotation = {r}
scene.textures.{n}_bump.mapping.uvscale = {su} {sv}
scene.textures.{n}_bump.mapping.uvdelta = {tu} {tv}
scene.textures.{n}.type = scale
scene.textures.{n}.texture1 = 0.01
scene.textures.{n}.texture2 = {n}_bump
"""
    elif propname == "normal":
        # Normal texture
        snippet = """
scene.textures.{n}.type = imagemap
scene.textures.{n}.file = "{f}"
scene.textures.{n}.gamma = {g}
scene.textures.{n}.mapping.type = uvmapping2d
scene.textures.{n}.mapping.rotation = {r}
scene.textures.{n}.mapping.uvscale = {su} {sv}
scene.textures.{n}.mapping.uvdelta = {tu} {tv}
"""
    else:
        # Plain texture
        snippet = """
scene.textures.{n}.type = imagemap
scene.textures.{n}.file = "{f}"
scene.textures.{n}.gamma = {g}
scene.textures.{n}.mapping.type = uvmapping2d
scene.textures.{n}.mapping.rotation = {r}
scene.textures.{n}.mapping.uvscale = {su} {sv}
scene.textures.{n}.mapping.uvdelta = {tu} {tv}
"""

    texture = snippet.format(
        n=texname,
        f=propvalue.file,
        r=float(propvalue.rotation),
        su=float(propvalue.scale_u),
        sv=float(propvalue.scale_v),
        tu=float(propvalue.translation_u),
        tv=float(propvalue.translation_v),
        g=gamma,
    )

    return texname, texture


VALSNIPPETS = {
    "RGB": "{val.r} {val.g} {val.b}",
    "float": "{val}",
    "node": "",
    "RGBA": "{val.r} {val.g} {val.b} {val.a}",
    "texonly": "{val}",
    "str": "{val}",
}


def _write_value(proptype, propvalue):
    """Compute a string in renderer SDL from a shader property value.

    Args:
        proptype -- Shader property's type
        propvalue -- Shader property's value

    The result depends on the type of the value...
    """
    # Snippets for values

    snippet = VALSNIPPETS[proptype]
    value = snippet.format(val=propvalue)
    return value


def _write_texref(texname):
    """Compute a string in SDL for a reference to a texture in a shader."""
    return texname


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

    def export_section(section, prefix, suffix):
        """Export a section to a temporary file."""
        f_handle, f_path = mkstemp(prefix=prefix, suffix="." + suffix)
        os.close(f_handle)
        result = [f"{k} = {v}" for k, v in dict(section).items()]
        with open(f_path, "w", encoding="utf-8") as output:
            output.write("\n".join(result))
        return f_path

    # LuxCore requires 2 files:
    # - a configuration file, with rendering parameters (engine, sampler...)
    # - a scene file, with the scene objects (camera, lights, meshes...)
    # So we have to generate both...

    # Get page result content (ie what the calling module baked for us)
    pageresult = configparser.ConfigParser(strict=False)  # Allow dupl. keys
    pageresult.optionxform = lambda option: option  # Case sensitive keys
    pageresult.read(project.PageResult)

    # Compute output
    output = (
        output if output else os.path.splitext(project.PageResult)[0] + ".png"
    )

    # Export configuration
    config = pageresult["Configuration"]
    config["film.width"] = str(width)
    config["film.height"] = str(height)
    config["film.outputs.0.type"] = "RGB_IMAGEPIPELINE"
    config["film.outputs.0.filename"] = output
    config["film.outputs.0.index"] = "0"
    config["periodicsave.film.outputs.period"] = "1"
    cfg_path = export_section(config, project.Name, "cfg")

    # Export scene
    scene = pageresult["Scene"]
    scn_path = export_section(scene, project.Name, "scn")

    # Get rendering parameters
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    args = params.GetString("LuxCoreParameters", "")
    rpath = params.GetString(
        "LuxCorePath" if external else "LuxCoreConsolePath", ""
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
