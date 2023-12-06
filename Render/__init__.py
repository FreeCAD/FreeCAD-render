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

It imports all the public symbols which make up the Render Workbench API.
"""


from Render.constants import (  # noqa: F401
    WBDIR,
    RDRDIR,
    ICONDIR,
    TRANSDIR,
    TEMPLATEDIR,
    PREFPAGE,
    TASKPAGE,
    RENDERERS,
    DEPRECATED_RENDERERS,
    VALID_RENDERERS,
    FCDVERSION,
)

from Render.project import Project, ViewProviderProject  # noqa: F401
from Render.view import View, ViewProviderView  # noqa: F401
from Render.camera import Camera, ViewProviderCamera  # noqa: F401
from Render.lights import (  # noqa: F401
    PointLight,
    ViewProviderPointLight,
    AreaLight,
    ViewProviderAreaLight,
    SunskyLight,
    ViewProviderSunskyLight,
    ImageLight,
    ViewProviderImageLight,
    DistantLight,
    ViewProviderDistantLight,
)
from Render.texture import Texture, ViewProviderTexture  # noqa: F401
from Render.material import (  # noqa: F401
    Material,
    ViewProviderMaterial,
    make_material,
)
from Render.utils import (  # noqa: F401
    reload,
    last_cmd,
    set_dryrun,
    set_dryrun_on,
    set_dryrun_off,
    set_debug,
    set_debug_on,
    set_debug_off,
    set_memcheck,
    set_memcheck_on,
    set_memcheck_off,
    set_a2p,
)
from Render.commands import RENDER_COMMANDS  # noqa: F401
from Render.prefpage import PreferencesPage  # noqa: F401
