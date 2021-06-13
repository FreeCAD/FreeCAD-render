# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2021 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements constants for Render workbench."""

import os
import re

import FreeCAD as App

# Paths to GUI resources
# This is for InitGui.py because it cannot import os
WBDIR = os.path.dirname(__file__)  # Workbench root directory
RDRDIR = os.path.join(WBDIR, "renderers")
ICONDIR = os.path.join(WBDIR, "resources", "icons")
TEMPLATEDIR = os.path.join(WBDIR, "templates")
TRANSDIR = os.path.join(WBDIR, "translations")
PREFPAGE = os.path.join(WBDIR, "resources", "ui", "RenderSettings.ui")
TASKPAGE = os.path.join(WBDIR, "resources", "ui", "RenderMaterial.ui")

# Renderers lists
RENDERERS = {x.group(1)
             for x in map(lambda x: re.match(r"^([A-Z].*)\.py$", x),
                          os.listdir(RDRDIR))
             if x}
DEPRECATED_RENDERERS = {"Luxrender"}
VALID_RENDERERS = sorted(RENDERERS - DEPRECATED_RENDERERS)

# FreeCAD version
FCDVERSION = App.Version()[0], App.Version()[1]  # FreeCAD version
