# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2024 Howefuft <howetuft-at-gmail>                       *
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

"""This module provides features to import MaterialX materials in Render WB."""

import zipfile
import tempfile
import os
import sys
import subprocess
import shutil
from contextlib import nullcontext

try:
    import MaterialX as mx
    from MaterialX import PyMaterialXGenShader as mx_gen_shader
    from MaterialX import PyMaterialXRender as mx_render
except (ModuleNotFoundError, ImportError):
    MATERIALX = False
else:
    MATERIALX = True

import FreeCAD as App

import Render.material
from Render.constants import MATERIALXDIR
from Render.materialx_baker import RenderTextureBaker


def import_materialx(zipname, *, debug=False):
    """Import a MaterialX archive into a material in Render.

    Args:
        zipname -- The path of the zip file containing the material
    """
    # MaterialX system available?
    if not MATERIALX:
        _warn("Missing MaterialX library: unable to import material")
        return

    if not debug:
        tmpdir_cm = tempfile.TemporaryDirectory()
    else:
        tmpdir_cm = nullcontext(
            tempfile.mkdtemp(dir=App.ActiveDocument.TransientDir)
        )

    # Proceed with file
    with zipfile.ZipFile(zipname, "r") as matzip:
        with tmpdir_cm as tmpdir:
            # Unzip material
            print(f"Extracting to {tmpdir}")
            matzip.extractall(path=tmpdir)

            # Find materialx file
            files = (
                entry.path
                for entry in os.scandir(tmpdir)
                if entry.is_file() and entry.name.endswith(".mtlx")
            )
            try:
                mtlx_name = next(files)
            except StopIteration:
                _warn("Missing mtlx file")
                return

            # Read doc
            mxdoc = mx.createDocument()
            mx.readFromXmlFile(mxdoc, mtlx_name)

            # Check material unicity and get its name
            if not (mxmats := mxdoc.getMaterialNodes()):
                _warn("No material in file")
                return
            if len(mxmats) > 1:
                _warn(f"Too many materials ({len(mxmats)}) in file")
                return
            mxmat = mxmats[0]
            mxname = mxmat.getName()

            # Clean doc for translation
            # Add own node graph
            if not (render_ng := mxdoc.getNodeGraph("RENDER_NG")):
                render_ng = mxdoc.addNodeGraph("RENDER_NG")

            # Move every cluttered root node to node graph
            exclude = {
                "nodedef",
                "nodegraph",
                "standard_surface",
                "surfacematerial",
                "displacement",
            }
            rootnodes = (
                n for n in mxdoc.getNodes() if n.getCategory() not in exclude
            )
            moved_nodes = set()
            for node in rootnodes:
                nodecategory = node.getCategory()
                nodename = node.getName()
                nodetype = node.getType()
                try:
                    newnode = render_ng.addNode(
                        nodecategory,
                        nodename + "_",
                        nodetype,
                    )
                except LookupError:
                    # Already exist
                    pass
                else:
                    newnode.copyContentFrom(node)
                    mxdoc.removeNode(nodename)
                    newnode.setName(nodename)
                    moved_nodes.add(nodename)

            # Connect shader inputs to node graph
            shader_inputs = (
                si
                for shader in mx.getShaderNodes(
                    materialNode=mxmat, nodeType=""
                )
                for si in shader.getInputs()
                if not si.hasValueString() and not si.getConnectedOutput()
            )
            for shader_input in shader_inputs:
                if (nodename := shader_input.getNodeName()) in moved_nodes:
                    # Create output node in node graph
                    newoutputname = f"{nodename}_output"
                    try:
                        newoutput = render_ng.addOutput(
                            name=newoutputname,
                            type=render_ng.getNode(nodename).getType(),
                        )
                    except LookupError:
                        pass
                    else:
                        newoutput.setNodeName(nodename)

                    # Connect input to output node
                    shader_input.setOutputString(newoutputname)
                    shader_input.setNodeGraphString("RENDER_NG")
                    shader_input.removeAttribute("nodename")

            # Compute search path
            search_path = mx.getDefaultDataSearchPath()
            search_path.append(tmpdir)
            search_path.append(MATERIALXDIR)

            # Import libraries
            mxlib = mx.createDocument()
            library_folders = mx.getDefaultDataLibraryFolders()
            library_folders.append("render_libraries")
            mx.loadLibraries(library_folders, search_path, mxlib)
            mxdoc.importLibrary(mxlib)
            outfile = _write_temp_doc(mxdoc)

            # Translate surface shader
            translator = mx_gen_shader.ShaderTranslator.create()
            try:
                translator.translateAllMaterials(mxdoc, "render_pbr")
            except mx.Exception as err:
                _warn(err)
                return

            # Translate displacement shader
            dispnodes = [
                s
                for r in mx_gen_shader.findRenderableMaterialNodes(mxdoc)
                for s in mx.getShaderNodes(
                    r, mx.DISPLACEMENT_SHADER_TYPE_STRING
                )
            ]
            try:
                for dispnode in dispnodes:
                    translator.translateShader(dispnode, "render_disp")
            except mx.Exception as err:
                _warn(err)
                return

            # Check the document for a UDIM set.
            udim_set_value = mxdoc.getGeomPropValue(mx.UDIM_SET_PROPERTY)
            udim_set = udim_set_value.getData() if udim_set_value else []

            # Compute baking resolution from the source document.
            image_handler = mx_render.ImageHandler.create(
                mx_render.StbImageLoader.create()
            )
            image_handler.setSearchPath(search_path)
            if udim_set:
                resolver = mxdoc.createStringResolver()
                resolver.setUdimString(udim_set[0])
                image_handler.setFilenameResolver(resolver)
            image_vec = image_handler.getReferencedImages(mxdoc)
            bake_width, bake_height = mx_render.getMaxDimensions(image_vec)
            bake_width = max(bake_width, 4)
            bake_height = max(bake_height, 4)

            # Bake surface shader
            # baker = mx_render_glsl.TextureBaker.create(
            # bake_width, bake_height, mx_render.BaseType.UINT8
            # )
            # _, outfile = tempfile.mkstemp(
            # suffix=".mtlx", dir=tmpdir, text=True
            # )
            # baker.setupUnitSystem(mxdoc)
            # baker.setDistanceUnit("meter")
            # baker.bakeAllMaterials(mxdoc, search_path, outfile)

            # TODO Move into separate function
            # material_node, disp_node = next(
            # (material, shader)
            # for shader in mx.getShaderNodes(
            # materialNode=material,
            # nodeType=mx.DISPLACEMENT_SHADER_TYPE_STRING,
            # )
            # for material in mx_gen_shader.findRenderableMaterialNodes(
            # mxdoc
            # )
            # )
            _, outfile = tempfile.mkstemp(
                suffix=".mtlx", dir=tmpdir, text=True
            )
            baker = RenderTextureBaker(
                bake_width,
                bake_height,
                mx_render.BaseType.UINT8,
            )
            # baker.setup_unit_system(mxdoc)
            baker.optimize_constants = True
            baker.hash_image_names = False
            baker.filename_template_var_override = "test"
            baker.bake_all_materials(
                mxdoc,
                search_path,
                outfile,
            )

            # Reset document to new file
            mxdoc = mx.createDocument()
            mx.readFromXmlFile(mxdoc, outfile)
            # _view_doc(mxdoc)
            # _run_materialx(outfile, "MaterialXGraphEditor")

            # Validate document
            valid, msg = mxdoc.validate()
            if not valid:
                msg = f"Validation warnings for input document: {msg}"
                _warn(msg)
                # return None

            # Get PBR material
            mxmats = mxdoc.getMaterialNodes()
            assert len(mxmats) == 1, f"len(mxmats) = {len(mxmats)}"
            mxmat = mxmats[0]

            # Get images
            node_graphs = mxdoc.getNodeGraphs()
            assert (
                len(node_graphs) <= 1
            ), f"len(node_graphs) = {len(node_graphs)}"
            if len(node_graphs):
                node_graph = node_graphs[0]
                images = {
                    node.getName(): node.getInputValue("file")
                    for node in node_graph.getNodes()
                    if node.getCategory() == "image"
                }
                outputs = {
                    node.getName(): node.getNodeName()
                    for node in node_graph.getOutputs()
                }
            else:
                images = {}
                outputs = {}

            # Get PBR
            all_pbr_nodes = [
                n for n in mxdoc.getNodes() if n.getCategory() == "render_pbr"
            ]

            # Log PBR
            sys.__stdout__.write(f"{outfile}\n")
            if debug:
                print(f"cd {tmpdir}")
                print(
                    f"MaterialXView --material {outfile} --path {MATERIALXDIR} --library render_libraries"
                )

            # TODO
            # Debug
            # _print_doc(mxdoc)
            # _print_file(outfile)
            # _run_materialx(outfile, "MaterialXGraphEditor")

            assert (
                len(all_pbr_nodes) == 1
            ), f"len(all_pbr_nodes) = {len(all_pbr_nodes)}"
            pbr_node = all_pbr_nodes[0]

            # TODO End 1st step

            # Create FreeCAD material
            #
            # Reminder: Material.Material is not updatable in-place (FreeCAD
            # bug), thus we have to copy/replace
            mat = Render.material.make_material(mxname)
            matdict = mat.Material.copy()
            matdict["Render.Type"] = "Disney"

            # Add textures, if necessary
            texture = None
            textures = {}
            for name, img in images.items():
                if not texture:
                    texture, _, _ = mat.Proxy.add_texture(img)
                    propname = "Image"
                else:
                    propname = texture.add_image(
                        imagename="Image", imagepath=img
                    )
                textures[name] = propname
            texname = texture.fpo.Name if texture else None

            # Fill fields
            for param in pbr_node.getInputs():
                if param.hasOutputString():
                    # Texture
                    output = param.getOutputString()
                    image = textures[outputs[output]]
                    name = param.getName()
                    key = f"Render.Disney.{name}"
                    if name != "Normal":
                        matdict[key] = f"Texture;('{texname}','{image}')"
                    else:
                        matdict[key] = (
                            f"Texture;('{texname}','{image}', '1.0')"
                        )
                elif name := param.getName():
                    # Value
                    key = f"Render.Disney.{name}"
                    matdict[key] = param.getValueString()
                else:
                    msg = f"Unhandled param: '{name}'"
                    _msg(msg)

            # Replace Material.Material
            mat.Material = matdict


# Debug functions


def _print_doc(mxdoc):
    """Print a doc in XML format (debugging purposes)."""
    as_string = mx.writeToXmlString(mxdoc)
    for line in as_string.splitlines():
        print(line)


def _print_file(outfile):
    """Print a doc in XML format (debugging purposes)."""
    with open(outfile, encoding="utf-8") as f:
        for line in f:
            print(line, end="")


def _write_temp_doc(mxdoc):
    """Write a MX document to a temporary file."""
    _, outfile = tempfile.mkstemp(suffix=".mtlx", text=True)
    mx.writeToXmlFile(mxdoc, outfile)
    return outfile


def _run_materialx(outfile, tool="MaterialXView"):
    """Run MaterialX on outfile (debug purpose)."""
    tool = str(tool)
    assert tool in ["MaterialXView", "MaterialXGraphEditor"]
    args = [
        tool,
        "--material",
        outfile,
        "--path",
        MATERIALXDIR,
        "--library",
        "render_libraries",
    ]
    print(args)
    subprocess.run(args, check=False)


def _save_intermediate(outfile):
    """Save intermediate material (debug purpose)."""
    src = os.path.dirname(outfile)
    folder = os.path.basename(src)
    dest = os.path.join(App.getUserCachePath(), folder)
    print(f"Copying '{src}' into '{dest}'")
    shutil.copytree(src, dest)


def _warn(msg):
    """Emit warning during MaterialX processing."""
    App.Console.PrintWarning("[Render][MaterialX] " + msg)


def _msg(msg):
    """Emit warning during MaterialX processing."""
    App.Console.PrintMessage("[Render][MaterialX] " + msg)


def _view_doc(doc):
    """Open copy of doc in editor."""
    outfile = _write_temp_doc(doc)
    subprocess.run(["/usr/bin/nvim", outfile], check=False)
