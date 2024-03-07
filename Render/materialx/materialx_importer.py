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

# TODO list
# Solve scale question
# Add Scale to Disney displacement (and to renderers...)
# Add icons
# Handle case when no MaterialX system installed
# Reorganize code: rename, create a subdir
# Write the doc
# Remove downloaded zip
# Explicit doc
# Fix texture dimensions
# Solve TODO: explicit doc etc.
# Handle HDR (set basetype to FLOAT, see translateshader.py)


import zipfile
import tempfile
import os
import threading
from dataclasses import dataclass
from typing import List, Tuple

import MaterialX as mx
from MaterialX import PyMaterialXGenShader as mx_gen_shader
from MaterialX import PyMaterialXRender as mx_render

import FreeCAD as App

import Render.material
from Render.constants import MATERIALXDIR

from .materialx_utils import (
    MaterialXInterrupted,
    MATERIALX,
    MaterialXError,
    _warn,
    _msg,
    critical_nomatx,
)
from .materialx_baker import RenderTextureBaker


class MaterialXImporter:
    """A class to import a MaterialX material into a RenderMaterial."""

    @dataclass
    class _ImporterState:
        """The internal state of the importer, for run method."""

        working_dir: str = ""  # Working directory
        mtlx_filename: str = ""  # Initial MaterialX file name
        search_path: mx.FileSearchPath = None
        substitutions: List[Tuple[str, str]] = None  # File substitutions
        translated: mx.Document = None  # Translated document
        baker: RenderTextureBaker = None  # Baker
        baked: mx.Document = None  # Baked document

    def __init__(self, filename, doc=None, progress_hook=None):
        self._filename = filename
        self._doc = doc or App.ActiveDocument
        self._baker_ready = threading.Event()
        self._request_halt = threading.Event()
        self._progress_hook = progress_hook

        self._state = MaterialXImporter._ImporterState()

    def run(self):
        """Import a MaterialX archive as Render material."""
        # MaterialX system available?
        if not MATERIALX:
            _warn("Missing MaterialX library: unable to import material")
            return -1

        # Proceed with file
        with tempfile.TemporaryDirectory() as working_dir:
            print("STARTING MATERIALX IMPORT")
            try:
                # Check wether there is a FreeCAD destination document
                if not self._doc:
                    raise MaterialXError(
                        "No target document for import. Aborting..."
                    )

                # Prepare
                self._state.working_dir = working_dir
                self._unzip_files()
                self._compute_search_path()

                # Translate, bake and convert to render material
                self._translate_materialx()
                self._compute_file_substitutions()
                self._prepare_baker()
                self._bake_materialx()
                self._make_render_material()

            except MaterialXInterrupted:
                print("IMPORT - INTERRUPTED")
                return -2
            except MaterialXError as error:
                print(f"IMPORT - ERROR - {error.message}")
                return -1

            print("IMPORT - SUCCESS")
            return 0

    def cancel(self):
        """Request process to halt.

        This command is designed to be executed in another thread than run.
        """
        self._request_halt.set()
        if self._baker_ready.is_set():
            self._baker.request_halt()

    def canceled(self):
        """Check if halt has been requested."""
        return self._request_halt.is_set()

    def _check_halt_requested(self):
        """Check if halt is requested, raise MaterialXInterrupted if so."""
        if self._request_halt.is_set():
            raise MaterialXInterrupted()

    # Helpers
    def _set_progress(self, value, maximum):
        """Report progress."""
        if self._progress_hook is not None:
            self._progress_hook(value, maximum)

    def _unzip_files(self):
        """Unzip materialx package, if needed.

        This method also set self._mtlx_filename
        """
        assert self._state.working_dir
        working_dir = self._state.working_dir

        if zipfile.is_zipfile(self._filename):
            if self._request_halt.is_set():
                raise MaterialXInterrupted()
            with zipfile.ZipFile(self._filename, "r") as matzip:
                # Unzip material
                print(f"Extracting to {working_dir}")
                matzip.extractall(path=working_dir)
                # Find materialx file
                files = (
                    entry.path
                    for entry in os.scandir(working_dir)
                    if entry.is_file() and entry.name.endswith(".mtlx")
                )
                try:
                    self._state.mtlx_filename = next(files)
                except StopIteration as exc:
                    raise MaterialXError("Missing mtlx file") from exc
        else:
            self._state.mtlx_filename = self._filename
        self._check_halt_requested()

    def _compute_search_path(self):
        """Compute search path for MaterialX."""
        assert self._state.working_dir
        assert self._state.mtlx_filename

        working_dir = self._state.working_dir
        mtlx_filename = self._state.mtlx_filename

        search_path = mx.getDefaultDataSearchPath()
        search_path.append(working_dir)
        search_path.append(os.path.dirname(mtlx_filename))
        search_path.append(MATERIALXDIR)

        self._state.search_path = search_path

    def _translate_materialx(self):
        """Translate MaterialX from StandardSurface to RenderPBR.

        Args:
            matdir -- The directory where to find MaterialX files
        """
        assert self._state.mtlx_filename
        assert self._state.search_path

        mtlx_filename = self._state.mtlx_filename
        search_path = self._state.search_path

        print("Translating material to Render format")

        # Read doc
        mxdoc = mx.createDocument()
        mx.readFromXmlFile(mxdoc, mtlx_filename)

        # Check material unicity and get its name
        if not (mxmats := mxdoc.getMaterialNodes()):
            raise MaterialXError("No material in file")
        if len(mxmats) > 1:
            raise MaterialXError(f"Too many materials ({len(mxmats)}) in file")
        mxmat = mxmats[0]

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
            for shader in mx.getShaderNodes(materialNode=mxmat, nodeType="")
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

        # Import libraries
        mxlib = mx.createDocument()
        library_folders = mx.getDefaultDataLibraryFolders()
        library_folders.append("render_libraries")
        mx.loadLibraries(library_folders, search_path, mxlib)
        mxdoc.importLibrary(mxlib)

        # Translate surface shader
        translator = mx_gen_shader.ShaderTranslator.create()
        try:
            translator.translateAllMaterials(mxdoc, "render_pbr")
        except mx.Exception as err:
            raise MaterialXError(
                "Translation error for surface shader"
            ) from err

        # Translate displacement shader
        dispnodes = [
            s
            for r in mx_gen_shader.findRenderableMaterialNodes(mxdoc)
            for s in mx.getShaderNodes(r, mx.DISPLACEMENT_SHADER_TYPE_STRING)
        ]
        try:
            for dispnode in dispnodes:
                translator.translateShader(dispnode, "render_disp")
        except mx.Exception as err:
            raise MaterialXError(
                "Translation error for displacement shader"
            ) from err

        self._state.translated = mxdoc

    def _compute_file_substitutions(self):
        """Compute file substitutions.

        If a file is missing, search for another file with similar
        case-insensitive name.
        """
        assert self._state.working_dir
        assert self._state.search_path
        assert self._state.translated

        working_dir = self._state.working_dir
        search_path = self._state.search_path
        mxdoc = self._state.translated

        # Available (normalized) files
        def rebuild_filename(dirpath, filename):
            relative_path = os.path.relpath(dirpath, working_dir)
            return os.path.normpath(os.path.join(relative_path, filename))

        available_files = {
            (dirpath, filename.lower()): rebuild_filename(dirpath, filename)
            for dirpath, _, filenames in os.walk(working_dir)
            for filename in filenames
        }

        # Unfound files
        working_dir_fp = mx.FilePath(working_dir)
        unfound_files = (
            (filename, working_dir_fp / filename.lower())
            for elem in mxdoc.traverseTree()
            if elem.getActiveSourceUri() == mxdoc.getSourceUri()
            and elem.getType() == mx.FILENAME_TYPE_STRING
            and not search_path.find(
                filename := elem.getResolvedValueString()
            ).exists()
        )
        unfound_files_dict = {
            filename: (
                filepath.getParentPath().asString(),
                filepath.getBaseName(),
            )
            for filename, filepath in unfound_files
        }

        # Substitutions
        self._state.substitutions = [
            (filename, available_files[pathkey])
            for filename, pathkey in unfound_files_dict.items()
            if pathkey in available_files
        ]

    def _prepare_baker(self):
        """Prepare MaterialX texture baker."""
        assert self._state.search_path
        assert self._state.translated
        assert self._state.substitutions is not None

        search_path = self._state.search_path
        mxdoc = self._state.translated
        substitutions = self._state.substitutions

        # Check the document for a UDIM set.
        udim_set_value = mxdoc.getGeomPropValue(mx.UDIM_SET_PROPERTY)
        udim_set = udim_set_value.getData() if udim_set_value else []

        # Compute baking resolution from the source document
        image_handler = mx_render.ImageHandler.create(
            mx_render.StbImageLoader.create()
        )
        image_handler.setSearchPath(search_path)
        resolver = mxdoc.createStringResolver()
        if udim_set:
            resolver.setUdimString(udim_set[0])
        for filename, substitute in substitutions:
            resolver.setFilenameSubstitution(filename, substitute)
        image_handler.setFilenameResolver(resolver)
        image_vec = image_handler.getReferencedImages(mxdoc)
        bake_width, bake_height = mx_render.getMaxDimensions(image_vec)
        bake_width = max(bake_width, 4)
        bake_height = max(bake_height, 4)

        # Prepare baker
        self._state.baker = RenderTextureBaker(
            bake_width,
            bake_height,
            mx_render.BaseType.UINT8,
        )
        self._state.baker.setup_unit_system(mxdoc)
        self._state.baker.optimize_constants = True
        self._state.baker.hash_image_names = False
        self._state.baker.progress_hook = self._progress_hook
        self._state.baker.filename_substitutions = substitutions

        self._baker_ready.set()

    def _bake_materialx(self):
        """Bake MaterialX material."""
        assert self._state.working_dir
        assert self._state.baker
        assert self._state.translated
        assert self._state.search_path

        output_dir = self._state.working_dir
        baker = self._state.baker
        mxdoc = self._state.translated
        search_path = self._state.search_path

        # Bake and retrieve
        _, outfile = tempfile.mkstemp(
            suffix=".mtlx", dir=output_dir, text=True
        )
        baker.bake_all_materials(mxdoc, search_path, outfile)

        mxdoc = mx.createDocument()
        mx.readFromXmlFile(mxdoc, outfile)

        # Validate document
        valid, msg = mxdoc.validate()
        if not valid:
            msg = f"Validation warnings for input document: {msg}"
            _warn(msg)

        self._state.baked = mxdoc

    def _make_render_material(self):
        """Make a RenderMaterial from a MaterialX baked material."""
        assert self._state.baked
        assert self._doc

        mxdoc = self._state.baked
        fcdoc = self._doc
        # Get PBR material
        # TODO Make it more predictable (name node_graph etc.)
        mxmats = mxdoc.getMaterialNodes()
        assert len(mxmats) == 1, f"len(mxmats) = {len(mxmats)}"
        mxmat = mxmats[0]
        mxname = mxmat.getAttribute("original_name")
        print(f"Creating FreeCAD Render material '{mxname}'")

        # Get images
        # TODO Make it more predictable (name node_graph etc.)
        node_graphs = mxdoc.getNodeGraphs()
        assert len(node_graphs) <= 1, f"len(node_graphs) = {len(node_graphs)}"
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

        # Reminder: Material.Material is not updatable in-place (FreeCAD
        # bug), thus we have to copy/replace
        mat = Render.material.make_material(name=mxname, doc=fcdoc)
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
                propname = texture.add_image(imagename="Image", imagepath=img)
            textures[name] = propname
        texname = texture.fpo.Name if texture else None

        # Fill fields
        render_params = (
            param
            for node in mxdoc.getNodes()
            for param in node.getInputs()
            if node.getCategory() in ("render_pbr", "render_disp")
        )
        for param in render_params:
            if param.hasOutputString():
                # Texture
                output = param.getOutputString()
                image = textures[outputs[output]]
                name = param.getName()
                key = f"Render.Disney.{name}"
                if name != "Normal":
                    matdict[key] = f"Texture;('{texname}','{image}')"
                else:
                    matdict[key] = f"Texture;('{texname}','{image}', '1.0')"
            elif name := param.getName():
                # Value
                key = f"Render.Disney.{name}"
                matdict[key] = param.getValueString()
            else:
                msg = f"Unhandled param: '{name}'"
                _msg(msg)

        # Replace Material.Material
        mat.Material = matdict


def import_materialx(filename, fcdoc):
    """Import MaterialX (function version)."""
    if not MATERIALX:
        critical_nomatx()
        return
    importer = MaterialXImporter(filename, fcdoc)
    importer.run()
