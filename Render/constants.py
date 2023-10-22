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

# Paths
PKGDIR = os.path.dirname(__file__)  # Package directory (=this file directory)
WBDIR = os.path.dirname(PKGDIR)  # Workbench root directory
RDRDIR = os.path.join(PKGDIR, "renderers")
ICONDIR = os.path.join(PKGDIR, "resources", "icons")
TEMPLATEDIR = os.path.join(WBDIR, "templates")
WBMATERIALDIR = os.path.realpath(os.path.join(WBDIR, "materials"))
FCDMATERIALDIR = os.path.join(
    App.getResourceDir(), "Mod", "Material", "StandardMaterial"
)
USERMATERIALDIR = os.path.join(App.ConfigGet("UserAppData"), "Materials")
TRANSDIR = os.path.join(PKGDIR, "resources", "translations")
PREFPAGE = os.path.join(PKGDIR, "resources", "ui", "RenderSettings.ui")
TASKPAGE = os.path.join(PKGDIR, "resources", "ui", "RenderMaterial.ui")

# Renderers lists
RENDERERS = {
    x.group(1)
    for x in map(lambda x: re.match(r"^([A-Z].*)\.py$", x), os.listdir(RDRDIR))
    if x
}
DEPRECATED_RENDERERS = {"Luxrender"}
VALID_RENDERERS = sorted(RENDERERS - DEPRECATED_RENDERERS)

# FreeCAD version
FCDVERSION = int(App.Version()[0]), float(App.Version()[1])

# Workbench parameters
PARAMS = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")

MAX_FILENAME_LEN = 256
