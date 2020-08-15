# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements some helpers for Render module"""


try:
    from draftutils.translate import translate as _translate  # 0.19
except ImportError:
    from Draft import translate as _translate  # 0.18

import FreeCAD as App


translate = _translate


def debug(domain, object_name, msg):
    """Print debug message"""
    msg = "[Render][{d}] '{n}': {m}\n".format(d=domain, n=object_name, m=msg)
    App.Console.PrintLog(msg)


def getproxyattr(obj, name, default):
    """Get attribute on object's proxy

    Behaves like getattr, but on Proxy property, and with mandatory default...
    """
    try:
        res = getattr(obj.Proxy, name, default)
    except AttributeError:
        res = default
    return res
