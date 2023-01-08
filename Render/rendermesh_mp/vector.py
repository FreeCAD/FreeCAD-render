# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2023 Howetuft <howetuft@gmail.com>                      *
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

"""Vector manipulation helpers."""

from math import sqrt
from operator import mul as op_mul, sub as op_sub

def add(*vectors):
    """Add 2 or more vectors."""
    return tuple(sum(x) for x in zip(*vectors))


def sub(vec1, vec2):
    """Substract 2 vectors."""
    return tuple(map(op_sub, vec1, vec2))


def fmul(vec, flt):
    """Multiply a vector by a float."""
    return tuple(x * flt for x in vec)


def fdiv(vec, flt):
    """Divide a vector by a float."""
    return tuple(x / flt for x in vec)


def barycenter(polygon):
    """Compute isobarycenter of a polygon."""
    return fdiv(add(*polygon), len(polygon))


def length(vec):
    """Compute vector length."""
    return sqrt(sum(x * x for x in vec))


def normal(triangle):
    """Compute the normal of a triangle."""
    # (p1 - p0) ^ (p2 - p0)
    point0, point1, point2 = triangle
    vec1 = sub(point1, point0)
    vec2 = sub(point2, point0)
    res = (
        vec1[1] * vec2[2] - vec1[2] * vec2[1],
        vec1[2] * vec2[0] - vec1[0] * vec2[2],
        vec1[0] * vec2[1] - vec1[1] * vec2[0],
    )
    return res


def dot(vec1, vec2):
    """Dot product."""
    return sum(map(op_mul, vec1, vec2))


def transform(matrix, vec):
    """Transform a 3D vector with a transformation matrix 4x4."""
    vec2 = (*vec, 1)
    return tuple(dot(line, vec2) for line in matrix[:-1])
