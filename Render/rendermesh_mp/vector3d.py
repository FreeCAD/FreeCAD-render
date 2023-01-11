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

"""Vector 3D manipulation helpers."""

from math import sqrt
from operator import mul as op_mul, sub as op_sub

def add_n(*vectors):
    """Add 2 or more vectors."""
    return tuple(sum(x) for x in zip(*vectors))

def add(vec1, vec2):
    """Add 2 vectors."""
    vec1_x, vec1_y, vec1_z = vec1
    vec2_x, vec2_y, vec2_z = vec2
    return vec1_x + vec2_x, vec1_y + vec2_y, vec1_z + vec2_z

def sub(vec1, vec2):
    """Substract 2 vectors."""
    vec1_x, vec1_y, vec1_z = vec1
    vec2_x, vec2_y, vec2_z = vec2
    return vec1_x - vec2_x, vec1_y - vec2_y, vec1_z - vec2_z

def fmul(vec, flt):
    """Multiply a vector by a float."""
    vec_x, vec_y, vec_z = vec
    return vec_x * flt, vec_y * flt, vec_z * flt


def fdiv(vec, flt):
    """Divide a vector by a float."""
    vec_x, vec_y, vec_z = vec
    return vec_x / flt, vec_y / flt, vec_z / flt


def barycenter(polygon):
    """Compute isobarycenter of a polygon."""
    return fdiv(add_n(*polygon), len(polygon))


def length(vec):
    """Compute vector length."""
    vec_x, vec_y, vec_z = vec
    return sqrt(vec_x * vec_x + vec_y * vec_y + vec_z * vec_z)


def normal(triangle):
    """Compute the normal of a triangle."""
    # (p1 - p0) ^ (p2 - p0)
    point0, point1, point2 = triangle
    vec1 = sub(point1, point0)
    vec2 = sub(point2, point0)
    vec1_x, vec1_y, vec1_z = vec1
    vec2_x, vec2_y, vec2_z = vec2
    res = (
        vec1_y * vec2_z - vec1_z * vec2_y,
        vec1_z * vec2_x - vec1_x * vec2_z,
        vec1_x * vec2_y - vec1_y * vec2_x,
    )
    return res


def dot(vec1, vec2):
    """Dot product."""
    vec1_x, vec1_y, vec1_z = vec1
    vec2_x, vec2_y, vec2_z = vec2
    return vec1_x * vec2_x + vec1_y * vec2_y + vec1_z * vec2_z

def dot4(vec1, vec2):
    """Dot product."""
    vec1_x, vec1_y, vec1_z, vec1_t = vec1
    vec2_x, vec2_y, vec2_z, vec2_t = vec2
    return vec1_x * vec2_x + vec1_y * vec2_y + vec1_z * vec2_z + vec1_t * vec2_t


def transform(matrix, vec):
    """Transform a 3D vector with a transformation matrix 4x4."""
    vec = (*vec, 1)
    return tuple(dot4(line, vec) for line in matrix[:-1])
