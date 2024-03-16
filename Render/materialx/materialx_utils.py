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

"""This module provides utilities for MaterialX handling system."""
import os
import subprocess
import shutil
import tempfile

from PySide2.QtWidgets import QMessageBox
from PySide2.QtWebEngineWidgets import QWebEngineProfile


try:
    import MaterialX as mx
except (ModuleNotFoundError, ImportError):
    MATERIALX = False
else:
    MATERIALX = True

import FreeCAD as App
import FreeCADGui as Gui

MATERIALXDIR = os.path.join(os.path.dirname(__file__), "materialx")


# Error handling


class MaterialXError(Exception):
    """Exception to be raised when import encounters an error."""

    def __init__(self, msg):
        super().__init__()
        self.message = str(msg)


class MaterialXInterrupted(Exception):
    """An exception to be raised when baker is interrupted."""


def critical_nomatx():
    """Emit critical error for missing materialx."""
    msg = (
        "Error: Cannot find MaterialX framework!\n"
        "Please check MaterialX is correctly installed on your system "
        "before using this feature..."
    )
    if App.GuiUp:
        QMessageBox.critical(Gui.getMainWindow(), "MaterialX Import", msg)
    else:
        App.Console.PrintError(msg)


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
