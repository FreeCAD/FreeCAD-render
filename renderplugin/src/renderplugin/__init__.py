# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Render addon.

################################################################################
#                                                                              #
#   © 2024 Howetuft <howetuft@gmail.com>                                       #
#                                                                              #
#   This addon is free software: you can redistribute it and/or modify         #
#   it under the terms of the GNU Lesser General Public License as             #
#   published by the Free Software Foundation, either version 2.1              #
#   of the License, or (at your option) any later version.                     #
#                                                                              #
#   This addon is distributed in the hope that it will be useful,              #
#   but WITHOUT ANY WARRANTY; without even the implied warranty                #
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.                    #
#   See the GNU Lesser General Public License for more details.                #
#                                                                              #
#   You should have received a copy of the GNU Lesser General Public           #
#   License along with this addon. If not, see https://www.gnu.org/licenses    #
#                                                                              #
################################################################################

"""This module implements framework for Render plugins.

The framework gives ability to plugins:
- to be embedded into FreeCAD Gui
- to communicate with Render and therefore with FreeCAD
"""

from .plugin_framework import (
    ARGS,
    RenderPluginApplication,
    PluginMessageEvent,
    log,
    msg,
    warn,
    error,
    SOCKET,
    SERVERNAME,
)
