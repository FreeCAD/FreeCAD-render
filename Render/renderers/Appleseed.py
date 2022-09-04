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

# NOTE Appleseed uses a different coordinate system than FreeCAD.
# Y and Z are switched and Z is inverted

import os
import re
import uuid
from tempfile import mkstemp
from math import pi, degrees, acos, atan2, sqrt
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

# TODO Move into Render.Mesh
def write_objfile(mesh, name, objfile=None, mtlfile=None, mtlname=None, normals=True):
    """Write an OBJ file from a mesh.

    Args:
        name -- Name of the mesh (str)
        objfile -- Name of the OBJ file (str). If None, the OBJ file is written
          in a temporary file, whose name is returned by the function.
        mtlfile -- MTL file name to reference in OBJ (optional) (str)
        mtlname -- Material name to reference in OBJ, must be defined in MTL
          file (optional) (str)
        normals -- Flag to control the writing of normals in the OBJ file
          (bool)

    Returns: the file that the function wrote.
    """

    # Retrieve and normalize arguments
    if objfile is None:
        f_handle, objfile = mkstemp(suffix=".obj", prefix="_")
        os.close(f_handle)
    else:
        objfile = str(objfile)

    normals = bool(normals)

    # Initialize
    header = ["# Written by FreeCAD-Render"]

    # Mtl
    mtl = [f"mtllib {mtlfile}", ""] if mtlfile is not None else []

    # Vertices
    verts = [p.Vector for p in mesh.Points]
    verts = [f"v {v.x} {v.y} {v.z}" for v in verts]
    verts.insert(0, "# Vertices")
    verts.append("")

    # UV
    if mesh.has_uvmap():
        uvs = [f"vt {t.x} {t.y}" for t in mesh.uvmap]
        uvs.insert(0, "# Texture coordinates")
        uvs.append("")
    else:
        uvs = []

    # Vertex normals
    if normals:
        norms = [f"vn {n.x} {n.y} {n.z}" for n in mesh.getPointNormals()]
        norms.insert(0, "# Vertex normals")
        norms.append("")
    else:
        norms = []

    # Object name
    objname = [f"o {name}"]
    if mtlname is not None:
        objname.append(f"usemtl {mtlname}")
    objname.append("")

    # Faces
    if normals and mesh.has_uvmap():
        mask = "{i}/{i}/{i}"
    elif not normals and mesh.has_uvmap():
        mask = "{i}/{i}"
    elif normals and not mesh.has_uvmap():
        mask = "{i}//{i}"
    else:
        mask = "{i}"

    faces = [map(lambda x: mask.format(i=x+1), f) for f in mesh.Topology[1]]
    faces = [" ".join(f) for f in faces]
    faces = [f"f {f}" for f in faces]
    faces.insert(0, "# Faces")

    res = header + mtl + verts + uvs + norms + objname + faces
    res = "\n".join(res)

    with open(objfile, "w", encoding="utf-8") as f:
        f.write(res)

    return objfile


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

    objfile = write_objfile(mesh, name, normals=False)

    # Transformation
    transform = TRANSFORM.copy()
    transform.multiply(mesh.Placement)
    transform.inverse()
    translines = [transform.Matrix.A[i*4:(i+1)*4] for i in range(4)]
    translines = ["{} {} {} {}".format(*l) for l in translines]

    # Format output
    mat_name = f"{name}.{uuid.uuid1()}"  # Avoid duplicate materials
    shortfilename = os.path.splitext(os.path.basename(objfile))[0]
    filename = objfile.encode("unicode_escape").decode("utf-8")

    snippet_mat = _write_material(mat_name, material)
    snippet_obj = f"""
            <object name="{shortfilename}" model="mesh_object">
                <parameter name="filename" value="{filename}" />
            </object>
            <object_instance name="{shortfilename}.{name}.instance" object="{shortfilename}.{name}" >
                <transform>
                    <matrix>
                        {translines[0]}
                        {translines[1]}
                        {translines[2]}
                        {translines[3]}
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


def _write_material_carpaint(name, material):
    """Compute a string in the renderer SDL for a carpaint material."""
    snippet = """
        <search_path>
            {s}
        </search_path>
    <!-- Generated by FreeCAD - Carpaint Shader -->
    <material name="{n}" model="osl_material">
        <parameter name="surface_shader" value="{n}_ss" />
        <parameter name="osl_surface" value="{n}_group" />
    </material>

    <surface_shader name="{n}_ss" model="physical_surface_shader" />

    <shader_group name="{n}_group">
        <shader layer="MasterMix" type="shader" name="as_standard_surface">
            <parameter name="in_color" value="color {c.r} {c.g} {c.b}" />
            <parameter name="in_diffuse_weight" value="float 0.8" />
            <parameter name="in_specular_color" value="color {c.r} {c.g} {c.b}" />
            <parameter name="in_specular_roughness" value="float 0.8" />
            <parameter name="in_fresnel_type" value="int 1" />
            <parameter name="in_face_tint" value="color 231 233 235" />
            <parameter name="in_edge_tint" value="color 212 219 227" />
            <parameter name="in_edge_tint_weight" value="float 0.1" />
            <parameter name="in_coating_absorption" value="color {c.r} {c.g} {c.b}" />
            <parameter name="in_coating_reflectivity" value="float 0.8" />
            <parameter name="in_coating_roughness" value="float 0.1" />
            <parameter name="in_coating_depth" value="float 0.001" />
            <parameter name="in_coating_ior" value="float 1.57" />
        </shader>
        <shader layer="Surface" type="surface" name="as_closure2surface" />

        <connect_shaders src_layer="MasterMix" src_param="out_outColor"
                         dst_layer="Surface" dst_param="in_input" />
    </shader_group>
    """

    return snippet.format(
        n=name,
        s=SHADERS_DIR.encode("unicode_escape").decode("utf-8"),
        c=material.carpaint.basecolor,  # Base
    )


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
