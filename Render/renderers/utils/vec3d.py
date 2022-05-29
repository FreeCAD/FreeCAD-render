# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2022 Howetuft <howetuft@gmail.com>                      *
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

"""3D vector for renderers plugins."""

import math
import numbers

class Vec3D:
    typecode = 'd'

    def __init__(self, x, y, z):
        self.__x = float(x)
        self.__y = float(y)
        self.__z = float(z)

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y

    @property
    def z(self):
        return self.__z

    def __iter__(self):
        return (i for i in (self.x, self.y, self.z))

    def __repr__(self):
        class_name = type(self).__name__
        return '{}({!r}, {!r}, {!r})'.format(class_name, *self)

    def __str__(self):
        return str(tuple(self))

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __hash__(self):
        return hash(self.x) ^ hash(self.y) ^ hash(self.z)

    def __abs__(self):
        return math.hypot(*self)

    def __bool__(self):
        return bool(abs(self))

    def angle(self):
        return math.atan2(self.y, self.x, self.z)

    def __format__(self):
        outer_fmt = "({}, {}, {})"
        components = (format(c, fmt_spec) for c in self)
        return outer_fmt.format(*components)

    def __add__(self, other):
        return Vec3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return Vec3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self):
        return Vec3D(-self.x, -self.y, -self.z)

    def __mul__(self, scalar):
        if isinstance(scalar, numbers.Real):
            return Vec3D(self.x * scalar, self.y * scalar, self.z * scalar)
        else:
            return NotImplemented

    def __rmul__(self, scalar):
        return self * scalar

    def __truediv__(self, scalar):
        if isinstance(scalar, numbers.Real):
            return Vec3D(self.x / scalar, self.y / scalar, self.z / scalar)
        else:
            return NotImplemented

    def normalize(self):
        size = abs(self)
        if not size:
            return 0
        return self / size
