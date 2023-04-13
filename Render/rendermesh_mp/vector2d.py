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

"""Vector 2D manipulation helpers."""

from math import sqrt
from operator import mul as op_mul, sub as op_sub


def add(vec1, vec2):
    """Add 2 vectors."""
    vec1_x, vec1_y = vec1
    vec2_x, vec2_y = vec2
    return vec1_x + vec2_x, vec1_y + vec2_y


def sub(vec1, vec2):
    """Substract 2 vectors."""
    vec1_x, vec1_y = vec1
    vec2_x, vec2_y = vec2
    return vec1_x - vec2_x, vec1_y - vec2_y


def fmul(vec, flt):
    """Multiply a vector by a float."""
    vec_x, vec_y = vec
    return vec_x * flt, vec_y * flt


def fdiv(vec, flt):
    """Divide a vector by a float."""
    vec_x, vec_y = vec
    return vec_x / flt, vec_y / flt


def length(vec):
    """Compute vector length."""
    vec_x, vec_y = vec
    return sqrt(vec_x * vec_x + vec_y * vec_y)


def dot(vec1, vec2):
    """Dot product."""
    vec1_x, vec1_y = vec1
    vec2_x, vec2_y = vec2
    return vec1_x * vec2_x + vec1_y * vec2_y
