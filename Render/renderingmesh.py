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

"""This module implements RenderingMesh class.

RenderingMesh is an extended version of FreeCAD Mesh.Mesh, designed for
rendering purpose.
"""

import math

import FreeCAD as App
import Mesh


class RenderingMesh:
    """An extended version of FreeCAD Mesh, designed for rendering.

    RenderingMesh is based on Mesh.Mesh and most of its API is common with
    the latter.
    In addition, RenderingMesh implements UV map management.

    Please note that RenderingMesh does not subclass Mesh.Mesh, as Mesh.Mesh is
    implemented in C, which prevents it to be subclassed in Python. As a
    workaround, the required methods and attributes are explicitly
    reimplemented as calls to the corresponding methods and attributes of
    Mesh.Mesh.
    """

    def __init__(self, mesh=None, uvmap=None):
        """Initialize RenderingMesh.

        Args:
            mesh -- a Mesh.Mesh object from which to initialize
            uvmap -- a given uv map for initialization
        """
        if mesh:
            self.__mesh = mesh
        else:
            self.__mesh = Mesh.Mesh()
        self.__uvmap = uvmap

    # Reexposed Mesh.Mesh methods and attributes
    def __repr__(self):
        """Give a printable representation of the object."""
        return self.__mesh.__repr__()

    def addFacet(self, *args):  # pylint: disable=invalid-name
        """Add a facet to the mesh."""
        self.__mesh.addFacet(*args)

    def copy(self):
        """Creates a copy of this mesh."""
        return RenderingMesh(self.__mesh.copy(), self.__uvmap)

    def getPointNormals(self):  # pylint: disable=invalid-name
        """Get the normals for each point."""
        return self.__mesh.getPointNormals()

    def harmonizeNormals(self):  # pylint: disable=invalid-name
        """Adjust wrong oriented facets."""
        self.__mesh.harmonizeNormals()

    def rotate(self, angle_x, angle_y, angle_z):
        """Apply a rotation to the mesh."""
        self.__mesh.rotate(angle_x, angle_y, angle_z)

    def transform(self, matrix):
        """Apply a transformation to the mesh."""
        self.__mesh.transform(matrix)

    def write(self, filename):
        """Write the mesh object into a file."""
        self.__mesh.write(filename)

    @property
    def Placement(self):  # pylint: disable=invalid-name
        """Get the current transformation of the object as placement."""
        return self.__mesh.Placement

    @property
    def Points(self):  # pylint: disable=invalid-name
        """Get a collection of the mesh points.

        With this attribute, it is possible to get access to the points of the
        mesh: for p in mesh.Points: print p.x, p.y, p.z,p.Index.

        WARNING! Store Points in a local variable as it is generated on the
        fly, each time it is accessed.
        """
        return self.__mesh.Points

    @property
    def Topology(self):  # pylint: disable=invalid-name
        """Get the points and faces indices as tuples.

        Topology[0] is a list of all vertices. Each being a tuple of 3
        coordinates. Topology[1] is a list of all polygons. Each being a list
        of vertex indice into Topology[0]

        WARNING! Store Topology in a local variable as it is generated on the
        fly, each time it is accessed.
        """
        return self.__mesh.Topology

    # Specific methods
    @property
    def uvmap(self):
        """Get mesh uv map."""
        return self.__uvmap

    def compute_uvmap(self):
        """Compute UV map for this mesh."""
        # Spherical mapping
        # TODO Beautify and use tuple
        res = []
        points = self.Points
        barycenter = compute_barycenter(points)
        for vertex in [(p.Vector - barycenter).normalize() for p in points]:
            # From https://en.wikipedia.org/wiki/UV_mapping
            vec = App.Base.Vector2d(
                0.5 + math.atan2(vertex.x, vertex.y) / (2 * math.pi),
                0.5 + math.asin(vertex.z) / math.pi,
            )
            res.append(vec)
        self.__uvmap = res

    def has_uvmap(self):
        """Check if object has a uv map."""
        return self.__uvmap is not None


def compute_barycenter(points):
    """Compute the barycenter of a list of points."""
    length = len(points)
    origin = App.Vector(0, 0, 0)
    if length == 0:
        return origin
    res = sum([p.Vector for p in points], origin) / length
    return res
