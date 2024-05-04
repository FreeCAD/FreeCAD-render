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

"""This module converts MaterialX material into FreeCAD material card.

This module is intended to run as a script. It takes a MaterialX filename
and outputs a FCMat file.
This module should not depend on FreeCAD libs in any way.
The aim of this module is to be run in a virtual environment where MaterialX
is installed. Using a virtual environment allows to install MaterialX with
pip even if system Python modules are externally managed.
"""

import zipfile
import tempfile
import os
import threading
from dataclasses import dataclass
from typing import List, Tuple
import argparse
import pathlib
import configparser
import json
import signal
import sys
import site

try:
    import MaterialX as mx
    from MaterialX import PyMaterialXGenShader as mx_gen_shader
    from MaterialX import PyMaterialXRender as mx_render
    from MaterialX import PyMaterialXFormat as mx_format
except (ModuleNotFoundError, ImportError):
    MATERIALX = False
else:
    MATERIALX = True

from materialx_baker import RenderTextureBaker

from materialx_utils import log, warn, error

MATERIALXDIR = os.path.dirname(__file__)
TEXNAME = "Texture"  # Texture name


class ConverterError(Exception):
    """Exception to be raised when import encounters an error."""

    MESSAGES = {
        255: "Interruption request",
        1: "Unhandled exception",
        2: "Missing mtlx file",
        3: "Unrecognized input format",
        4: "No material in file",
        5: "Too many materials in file",
        6: "Translation error for surface shader",
        7: "Translation error for displacement shader",
        8: "Invalid destination directory",
        9: "Missing MaterialX library: unable to convert material",
    }

    def __init__(self, errno):
        super().__init__()
        self.errno = errno

    @property
    def message(self):
        """Get error message."""
        return self.MESSAGES.get(self.errno, "Unknown error.")


class MaterialXConverter:
    """A class to import a MaterialX material into a RenderMaterial."""

    @dataclass
    class _ConverterState:
        """The internal state of the converter, for run method."""

        mtlx_filename: str = ""  # Initial MaterialX file name
        search_path: mx.FileSearchPath = None
        mtlx_input_doc: mx.Document = None
        substitutions: List[Tuple[str, str]] = None  # File substitutions
        translated: mx.Document = None  # Translated document
        baker: RenderTextureBaker = None  # Baker
        baked: mx.Document = None  # Baked document

    def __init__(
        self,
        filename: str,
        destdir: str,
        disp2bump: bool = False,
        polyhaven_size: float = None,
    ):
        """Initialize converter.

        Args:
            filename -- the name of the file to import
            destdir -- destination directory, where to collect inputs and
              deposit outputs
            progress_hook -- a hook to call to report progress (current, max)
            disp2bump -- a flag to set bump with displacement
        """
        self._filename = str(filename)
        self._destdir = str(destdir)
        self._disp2bump = bool(disp2bump)
        self._polyhaven_size = polyhaven_size

        self._baker_ready = threading.Event()
        self._request_halt = threading.Event()

        self._state = MaterialXConverter._ConverterState()

    def run(self):
        """Import a MaterialX archive as Render material."""
        # Prepare
        self._unzip_files()
        self._compute_search_path()

        # Read, translate, bake and convert to render material
        self._read_materialx()
        self._translate_materialx()
        self._correct_polyhaven_size()
        self._compute_file_substitutions()
        self._prepare_baker()
        self._bake_materialx()
        self._write_fcmat()

    def cancel(self):
        """Request process to halt.

        This command is designed to be executed in another thread than run.
        """
        self._request_halt.set()
        if self._baker_ready.is_set():
            self._state.baker.request_halt()

    def canceled(self):
        """Check if halt has been requested."""
        return self._request_halt.is_set()

    def _unzip_files(self):
        """Unzip materialx package, if needed.

        This method also set self._mtlx_filename
        """
        working_dir = self._destdir

        if zipfile.is_zipfile(self._filename):
            if self._request_halt.is_set():
                raise ConverterError(255)  # Interrupted
            with zipfile.ZipFile(self._filename, "r") as matzip:
                # Unzip material
                log(f"Extracting to {working_dir}")
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
                    raise ConverterError(2) from exc
        else:
            self._state.mtlx_filename = self._filename

    def _compute_search_path(self):
        """Compute search path for MaterialX."""
        assert self._state.mtlx_filename

        working_dir = self._destdir
        mtlx_filename = self._state.mtlx_filename

        search_path = mx.getDefaultDataSearchPath()
        search_path.append(working_dir)
        search_path.append(os.path.dirname(mtlx_filename))
        search_path.append(MATERIALXDIR)
        if sys.prefix != sys.base_prefix:  # Virtual environment
            for path in site.getsitepackages():
                path = os.path.join(path, "MaterialX")
                search_path.append(path)

        self._state.search_path = search_path

    def _read_materialx(self):
        """Read materialx file to translate."""
        assert self._state.mtlx_filename

        log("Reading MaterialX file")

        # Read doc
        mxdoc = mx.createDocument()
        try:
            mx.readFromXmlFile(mxdoc, self._state.mtlx_filename)
        except mx_format.ExceptionParseError as err:
            raise ConverterError(3) from err

        # Check material unicity and get its name
        if not (mxmats := mxdoc.getMaterialNodes()):
            raise ConverterError(4)
        if len(mxmats) > 1:
            raise ConverterError(5)
        mxmat = mxmats[0]

        # Clean doc for translation
        # Add own node graph
        if not (render_ng := mxdoc.getNodeGraph("RENDER_NG")):
            render_ng = mxdoc.addNodeGraph("RENDER_NG")

        # Move every cluttered root node to node graph
        rootnodes = (
            n
            for n in mxdoc.getNodes()
            if n.getCategory()
            not in {
                "nodedef",
                "nodegraph",
                "standard_surface",
                "surfacematerial",
                "displacement",
            }
        )
        moved_nodes = set()
        for node in rootnodes:
            nodename = node.getName()
            try:
                newnode = render_ng.addNode(
                    node.getCategory(),
                    nodename + "_",
                    node.getType(),
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

        # Update state
        self._state.mtlx_input_doc = mxdoc

    def _translate_materialx(self):
        """Translate MaterialX from StandardSurface to RenderPBR."""
        log("Translating material to Render format")

        assert self._state.search_path
        assert self._state.mtlx_input_doc

        search_path = self._state.search_path
        mxdoc = self._state.mtlx_input_doc

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
            raise ConverterError(6) from err

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
            raise ConverterError(7) from err

        self._state.translated = mxdoc

    def _correct_polyhaven_size(self):
        """Fix polyhaven size if an actual size has been given.

        In gpuopen, materials translated from polyhaven.com frequently have
        wrong size. This hook fixes this bug, if a substitute size has been
        given.
        """
        if not (size := self._polyhaven_size):
            return
        mxdoc = self._state.translated

        assert mxdoc

        uvnodes = (
            elem for elem in mxdoc.traverseTree() if elem.getName() == "uv"
        )

        try:
            uvnode = next(uvnodes)
        except StopIteration:
            return

        log(
            "Polyhaven material detected: will use actual texture size from "
            "polyhaven.com "
            f"('{size} {'meters' if size > 1 else 'meter'}')"
        )

        value = uvnode.getInput("value")
        value.setAttribute("value", str(1 / size))

    def _compute_file_substitutions(self):
        """Compute file substitutions.

        If a file is missing, search for another file with similar
        case-insensitive name.
        """
        assert self._state.search_path
        assert self._state.translated

        working_dir = self._destdir
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
        self._state.baker.progress_hook = _set_progress
        self._state.baker.filename_substitutions = substitutions

        self._baker_ready.set()

    def _bake_materialx(self):
        """Bake MaterialX material."""
        assert self._state.baker
        assert self._state.translated
        assert self._state.search_path

        output_dir = self._destdir
        baker = self._state.baker
        mxdoc = self._state.translated
        search_path = self._state.search_path

        # Bake and retrieve
        handle, outfile = tempfile.mkstemp(
            suffix=".mtlx", dir=output_dir, text=True
        )
        os.close(handle)
        baker.bake_all_materials(mxdoc, search_path, outfile)

        mxdoc = mx.createDocument()
        mx.readFromXmlFile(mxdoc, outfile)

        # Validate document
        valid, msg = mxdoc.validate()
        if not valid:
            warning = f"Validation warnings for input document: {msg}"
            warn(warning)

        self._state.baked = mxdoc

    def _write_fcmat(self):
        """Make a FCMat file from a MaterialX baked material."""

        assert self._state.baked
        mxdoc = self._state.baked

        # Get PBR material
        mxmats = mxdoc.getMaterialNodes()
        assert len(mxmats) == 1, f"len(mxmats) = {len(mxmats)}"
        mxmat = mxmats[0]
        mxname = mxmat.getAttribute("original_name")

        outfilename = os.path.join(self._destdir, "out.FCMat")
        log(f"Creating material card: {outfilename}")

        # Get images
        images, outputs = _get_images_from_mxdoc(mxdoc)

        # Reminder: Material.Material is not updatable in-place (FreeCAD
        # bug), thus we have to copy/replace
        matdict = {}
        matdict["Render.Type"] = "Disney"

        # Fill fields of material dictionary
        matdict.update(_get_fcmat_fields(mxdoc, self._disp2bump, outputs, images))

        # Write FCMat
        _write_fcmat_to_disk(matdict, mxname, outfilename)


# Helpers
def _get_images_from_mxdoc(mxdoc):
    """Get images from MaterialX document."""
    node_graphs = mxdoc.getNodeGraphs()
    assert len(node_graphs) <= 1, f"len(node_graphs) = {len(node_graphs)}"
    try:
        node_graph = node_graphs[0]
    except IndexError:
        images = {}
        outputs = {}
    else:
        images = {
            node.getName(): node.getInputValue("file")
            for node in node_graph.getNodes()
            if node.getCategory() == "image"
        }
        outputs = {
            node.getName(): node.getNodeName()
            for node in node_graph.getOutputs()
        }
    return images, outputs


def _get_fcmat_fields(mxdoc, disp2bump, outputs, images):
    """Get FCMat fields from mxdoc."""
    matdict = {}

    # Handle textures, if necessary
    textures = {}
    for index, item in enumerate(images.items()):
        name, img = item
        matdict[f"Render.Textures.{TEXNAME}.Images.{index}"] = img
        textures[name] = index

    render_params = (
        (param, param.getName())
        for node in mxdoc.getNodes()
        for param in node.getInputs()
        if node.getCategory() in ("render_pbr", "render_disp")
    )
    for param, name in render_params:
        if name == "Displacement" and disp2bump:
            name = "Bump"  # Substitute bump to displacement
        if param.hasOutputString():
            # Texture
            output = param.getOutputString()
            index = textures[outputs[output]]
            key = f"Render.Disney.{name}"
            if name not in ("Normal", "Bump"):
                matdict[key] = f"Texture('{TEXNAME}', {index})"
            else:
                matdict[key] = f"Texture('{TEXNAME}', {index}, 1.0)"
        elif name:
            # Value
            key = f"Render.Disney.{name}"
            matdict[key] = param.getValueString()
        else:
            msg = f"Unhandled param: '{name}'"
            warn(msg)
    return matdict


def _write_fcmat_to_disk(matdict, name, outfilename):
    """Write material to disk, as a FCMat file."""
    config = configparser.ConfigParser()
    config.optionxform = str  # Case sensitive
    config["General"] = {"Name": name}
    config["Render"] = matdict
    with open(outfilename, "w", encoding="utf-8") as out:
        config.write(out)


def _set_progress(value, maximum):
    """Report progress."""
    msg = json.dumps({"value": value, "maximum": maximum})
    log(msg)


def _interrupt(signum, stackframe):
    """Interrupt treatment."""
    raise ConverterError(255)


def _check_materialx():
    """Check whether MaterialX is available."""
    # MaterialX system available?
    if not MATERIALX:
        raise ConverterError(9)


def _get_destdir(args):
    """Get destination directory from arguments."""
    destdir = args.destdir.resolve()
    if not destdir.exists() or not destdir.is_dir():
        raise ConverterError(8)
    return destdir


# Main
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=argparse.FileType("r"))
    parser.add_argument("destdir", type=pathlib.Path)
    parser.add_argument("--polyhaven-size", type=float)
    parser.add_argument("--disp2bump", action="store_true")
    program_args = parser.parse_args()

    try:
        signal.signal(signal.SIGTERM, _interrupt)
        _check_materialx()
        _destdir = _get_destdir(program_args)

        converter = MaterialXConverter(
            program_args.file.name,
            str(_destdir),
            polyhaven_size=program_args.polyhaven_size,
            disp2bump=program_args.disp2bump,
        )
        converter.run()
    except ConverterError as main_err:
        error(f"CONVERTER EXCEPTION #{main_err.errno}: {main_err.message}")
        sys.exit(main_err.errno)

    sys.exit(0)
