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

import os
import threading
from typing import Callable
import subprocess
import json
import sys

from renderplugin import msg, warn, error


class MaterialXImporter:
    """A class to import a MaterialX material into a FCMat file."""

    def __init__(
        self,
        filename: str,
        progress_hook: Callable[[int, int], None] = None,
        disp2bump: bool = False,
        polyhaven_size: float = None,
    ):
        """Initialize importer.

        Args:
            filename -- the name of the file to import
            progress_hook -- a hook to call to report progress (current, max)
            disp2bump -- a flag to set bump with displacement
            polyhaven_size -- the size of the textures, from polyhaven.com
        """
        self._filename = filename
        self._baker_ready = threading.Event()
        self._request_halt = threading.Event()
        self._progress_hook = progress_hook
        self._disp2bump = disp2bump
        self._polyhaven_size = polyhaven_size
        self._proc = None

    def run(self, working_dir):
        """Import a MaterialX archive as Render material."""
        executable = sys.executable
        script = os.path.join(
            os.path.dirname(__file__), "converter", "materialx_converter.py"
        )

        msg("STARTING MATERIALX IMPORT")

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
                    for subline in line.splitlines():
                        msg(subline)
                else:
                    # Report progress
                    if self._progress_hook:
                        self._progress_hook(decode["value"], decode["maximum"])

        # Check result
        if (returncode := proc.returncode) != 0:
            if returncode == 255:
                warn("IMPORT - INTERRUPTED")
            else:
                error(f"IMPORT - ABORTED ({returncode})")
            return returncode

        return 0

    def cancel(self):
        """Request process to halt.

        This command is designed to be executed in another thread than run.
        """
        if self._proc:
            self._proc.terminate()
