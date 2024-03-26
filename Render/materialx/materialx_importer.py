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
#
# Version1
# Write documentation
# Write announcement
# Assign material with right-click
# Address 0.22 compatibility
# Handle HDRI IBL download
#
# Version 2
# Add a mix normal/height map to Ospray
# Povray: adapt Disney (clearcoat etc.)
# Handle HDR (set basetype to FLOAT, see translateshader.py)
# Add Poly Haven (gltf)


import zipfile
import tempfile
import os
import threading
from dataclasses import dataclass
from typing import List, Tuple, Callable
import subprocess
import json

import FreeCAD as App
import importFCMat

import Render.material
from Render.constants import MATERIALXDIR
from Render.utils import find_python

from .materialx_utils import (
    MaterialXInterrupted,
    MATERIALX,
    MaterialXError,
    _warn,
    _msg,
    critical_nomatx,
)


class MaterialXImporter:
    """A class to import a MaterialX material into a RenderMaterial."""

    def __init__(
        self,
        filename: str,
        doc: App.Document = None,
        progress_hook: Callable[[int, int], None] = None,
        disp2bump: bool = False,
        polyhaven_size: float = None,
    ):
        """Initialize importer.

        Args:
            filename -- the name of the file to import
            doc -- the FreeCAD document where to create material
            progress_hook -- a hook to call to report progress (current, max)
            disp2bump -- a flag to set bump with displacement
        """
        self._filename = filename
        self._doc = doc or App.ActiveDocument
        self._baker_ready = threading.Event()
        self._request_halt = threading.Event()
        self._progress_hook = progress_hook
        self._disp2bump = disp2bump
        self._polyhaven_size = polyhaven_size

    def run(self):
        """Import a MaterialX archive as Render material."""
        executable = find_python()
        script = os.path.join(
            os.path.dirname(__file__), "materialx_converter.py"
        )
        # Proceed with file
        with tempfile.TemporaryDirectory() as working_dir:
            print("STARTING MATERIALX IMPORT")
            try:
                # Check wether there is a FreeCAD destination document
                if not self._doc:
                    raise MaterialXError(
                        "No target document for import. Aborting..."
                    )

                # Prepare converter call
                args = [executable, "-u", script, self._filename, working_dir]
                if self._polyhaven_size:
                    args += ["--polyhaven-size", self._polyhaven_size]
                if self._disp2bump:
                    args += ["--disp2bump"]

                # Run converter
                with subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=0,  # Unbuffered
                    universal_newlines=True,
                ) as proc:
                    for line in proc.stdout:
                        try:
                            decode = json.loads(line)
                        except json.JSONDecodeError:
                            # Undecodable: write as-is
                            App.Console.PrintMessage(line)
                        else:
                            # Should be a progress report
                            if self._progress_hook:
                                self._progress_hook(
                                    decode["value"], decode["maximum"]
                                )

                # Import result
                in_file = os.path.join(working_dir, "out.FCMat")
                matdict = importFCMat.read(in_file)
                mxname = matdict.get("Name", "Material")
                mat = Render.material.make_material(name=mxname, doc=self._doc)
                matdict = mat.Proxy.import_textures(matdict, basepath=None)

                # Reminder: Material.Material is not updatable in-place
                # (FreeCAD bug), thus we have to copy/replace
                mat.Material = matdict
            # TODO Exception handling
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
            self._state.baker.request_halt()

    def canceled(self):
        """Check if halt has been requested."""
        return self._request_halt.is_set()

    def _check_halt_requested(self):
        """Check if halt is requested, raise MaterialXInterrupted if so."""
        if self._request_halt.is_set():
            raise MaterialXInterrupted()


def import_materialx(filename, fcdoc):
    """Import MaterialX (function version)."""
    importer = MaterialXImporter(filename, fcdoc)
    importer.run()
