# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2023 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
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

"""Miscellaneous utilities for renderers."""

from math import radians, degrees, tan, atan


def fovy_to_fovx(fovy, width, height):
    """Convert vertical field of view (fovy) to horizontal (fovx).

    This function is useful for renderers that expect horizontal field of view,
    like Luxcore, Appleseed and Povray. Indeed, FreeCAD camera fov is a
    vertical one...

    Args:
        fovy -- Vertical field of view, in degrees (float)
        width -- Width of frame (float)
        height -- Height of frame (float)

    Returns:
        Horizontal field of view, in degrees (float)
    """
    assert width > 0
    assert height > 0
    aspect_ratio = width / height
    fovy = radians(fovy)
    fovx = 2 * atan(tan(fovy / 2) * aspect_ratio)
    fovx = degrees(fovx)
    return fovx
