# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Render addon.

################################################################################
#                                                                              #
#   © 2023 Howetuft <howetuft@gmail.com>                                       #
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
