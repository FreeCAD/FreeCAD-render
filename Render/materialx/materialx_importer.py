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


import tempfile
import os
import threading
from typing import Callable
import subprocess
import json
import configparser

import FreeCAD as App

import Render.material
from Render.virtualenv import get_venv_python


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
        self._proc = None

    def run(self):
        """Import a MaterialX archive as Render material."""
        executable = get_venv_python()
        script = os.path.join(
            os.path.dirname(__file__), "converter", "materialx_converter.py"
        )
        # Proceed with file
        with tempfile.TemporaryDirectory() as working_dir:
            print("STARTING MATERIALX IMPORT")
            # Check wether there is a FreeCAD destination document
            if not self._doc:
                print("No target document for import. Aborting...")
                return -1

            # Prepare converter call
            args = [executable, "-u", script, self._filename, working_dir]
            if self._polyhaven_size:
                args += ["--polyhaven-size", str(self._polyhaven_size)]
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
                self._proc = proc
                for line in proc.stdout:
                    try:
                        decode = json.loads(line)
                    except json.JSONDecodeError:
                        # Undecodable: write as-is
                        App.Console.PrintMessage(line)
                    else:
                        # Report progress
                        if self._progress_hook:
                            self._progress_hook(
                                decode["value"], decode["maximum"]
                            )

            # Check result
            if (returncode := proc.returncode) != 0:
                if returncode == 255:
                    App.Console.PrintWarning("IMPORT - INTERRUPTED\n")
                else:
                    App.Console.PrintError(
                        f"IMPORT - ABORTED ({returncode})\n"
                    )
                return returncode

            # Import result
            in_file = os.path.join(working_dir, "out.FCMat")
            card = configparser.ConfigParser()
            card.optionxform = lambda x: x  # Case sensitive
            card.read(in_file)
            try:
                mxname = card["General"]["Name"]
            except LookupError:
                mxname = "Material"
            matdict = dict(card["Render"])
            mat = Render.material.make_material(name=mxname, doc=self._doc)
            matdict = mat.Proxy.import_textures(matdict, basepath=None)

            # Reminder: Material.Material is not updatable in-place
            # (FreeCAD bug), thus we have to copy/replace
            mat.Material = matdict

            print("IMPORT - SUCCESS")
            return 0

    def cancel(self):
        """Request process to halt.

        This command is designed to be executed in another thread than run.
        """
        if self._proc:
            self._proc.terminate()


def import_materialx(filename, fcdoc):
    """Import MaterialX (function version)."""
    importer = MaterialXImporter(filename, fcdoc)
    importer.run()
