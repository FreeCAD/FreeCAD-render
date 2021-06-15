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


"""This is Render workbench main module.

It provides the necessary objects to deal with rendering:
- GUI Commands
- Rendering Projects and Views

On initialization, this module will retrieve all renderer modules and create
the necessary UI controls.
"""


from Render.constants import (WBDIR, RDRDIR, ICONDIR, TRANSDIR,  # noqa: F401
                              TEMPLATEDIR, PREFPAGE, TASKPAGE, RENDERERS,
                              DEPRECATED_RENDERERS, VALID_RENDERERS,
                              FCDVERSION)

from Render.project import Project, ViewProviderProject  # noqa: F401
from Render.view import View, ViewProviderView  # noqa: F401
from Render.camera import Camera, ViewProviderCamera  # noqa: F401
from Render.lights import (PointLight, ViewProviderPointLight,  # noqa: F401
                           AreaLight, ViewProviderAreaLight,
                           SunskyLight, ViewProviderSunskyLight,
                           ImageLight, ViewProviderImageLight)
from Render.utils import reload
from Render.commands import RENDER_COMMANDS  # noqa: F401
