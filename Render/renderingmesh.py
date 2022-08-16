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
import enum

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

    def __init__(self, mesh=None, uvmap=None, placement=App.Base.Placement()):
        """Initialize RenderingMesh.

        Args:
            mesh -- a Mesh.Mesh object from which to initialize
            uvmap -- a given uv map for initialization
        """
        if mesh:
            self.__mesh = mesh
            assert mesh.Placement == App.Base.Placement()
            self.__originalmesh = mesh.copy()
            self.__originalmesh.transform(placement.inverse().Matrix)
            self.__originalplacement = placement.copy()
            # At the moment (08-16-2022), the mesh is generated with a null
            # placement as the plugins don't know how to manage a non-null
            # placement. However, for uv mapping, we have to turn back to this
            # primary placement which is useful This is not a very clean way to
            # do, so one day we'll have to manage placements in renderers
            # (TODO).
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

    def compute_uvmap(self, projection):
        """Compute UV map for this mesh."""
        barycenter = _compute_barycenter(self.Points)
        # self._compute_uvmap_sphere(barycenter)
        self._compute_uvmap_cube(barycenter)

    # TODO
    # Useful resources:
    #  https://www.pixyz-software.com/documentations/html/2021.1/studio/UVProjectionTool.html

    def _compute_uvmap_sphere(self, origin):
        """Compute UV map for spherical case."""
        vectors = [(p.Vector - origin).normalize() for p in self.Points]
        self.__uvmap = tuple(
            App.Base.Vector2d(
                0.5 + math.atan2(v.x, v.y) / (2 * math.pi),
                0.5 + math.asin(v.z) / math.pi,
            )
            for v in vectors
        )

    def _compute_uvmap_cube(self, origin):
        """Compute UV map for cubic case.

        We isolate submeshes by cube face in order to avoid trouble when
        one edge belongs to several cube faces (cf. simple cube case, for
        instance)
        """
        origin = App.Base.Vector(0, 0, 0)
        # Isolate submeshes by cube face
        face_facets = {f: [] for f in _UnitCubeFaceEnum}
        for facet in self.__originalmesh.Facets:
            # Determine which cubeface the facet belongs to
            cubeface = _intersect_unitcube_face(facet.Normal)
            # Add facet to corresponding submesh
            face_facets[cubeface].append(facet)

        # Rebuid a complete mesh from face submeshes, with uvmap
        uvmap = []
        mesh = Mesh.Mesh()
        for cubeface, facets in face_facets.items():
            facemesh = Mesh.Mesh(facets)
            # Compute uvmap of the submesh
            facemesh_uvmap = [
                _compute_uv_from_unitcube(p.Vector / 1000, cubeface)
                # pylint: disable=not-an-iterable
                for p in facemesh.Points
            ]
            # Add submesh and uvmap
            facemesh.transform(self.__originalplacement.Matrix)
            mesh.addMesh(facemesh)
            uvmap += facemesh_uvmap

        # Replace previous values with newly computed ones
        self.__mesh = mesh
        self.__uvmap = tuple(uvmap)

    def has_uvmap(self):
        """Check if object has a uv map."""
        return self.__uvmap is not None


# ===========================================================================
#                           Cube uvmap helpers
# ===========================================================================


class _UnitCubeFaceEnum(enum.Enum):
    """A class to describe a face of a unit cube.

    A unit cube is cube centered on the origin, each face perpendicular to one
    of the axes of the reference frame and the distance from the origin to each
    face being equal to 1.
    This cube is useful for projections for uv map...
    """

    XPLUS = enum.auto()
    XMINUS = enum.auto()
    YPLUS = enum.auto()
    YMINUS = enum.auto()
    ZPLUS = enum.auto()
    ZMINUS = enum.auto()


# Normals of the faces of the unit cube
_UNIT_CUBE_FACES_NORMALS = {
    _UnitCubeFaceEnum.XPLUS: (1.0, 0.0, 0.0),
    _UnitCubeFaceEnum.XMINUS: (-1.0, 0.0, 0.0),
    _UnitCubeFaceEnum.YPLUS: (0.0, 1.0, 0.0),
    _UnitCubeFaceEnum.YMINUS: (0.0, -1.0, 0.0),
    _UnitCubeFaceEnum.ZPLUS: (0.0, 0.0, 1.0),
    _UnitCubeFaceEnum.ZMINUS: (0.0, 0.0, -1.0),
}


def _intersect_unitcube_face(direction):
    """Get the face of the unit cube intersected by a line from origin.

    Args:
        direction -- The directing vector for the intersection line
        (a 3-float sequence)

    Returns:
        A face from the unit cube (_UnitCubeFaceEnum)
    """
    dabs = (abs(direction[0]), abs(direction[1]), abs(direction[2]))

    if dabs[0] >= dabs[1] and dabs[0] >= dabs[2]:
        return (
            _UnitCubeFaceEnum.XPLUS
            if direction[0] >= 0
            else _UnitCubeFaceEnum.XMINUS
        )

    if dabs[1] >= dabs[0] and dabs[1] >= dabs[2]:
        return (
            _UnitCubeFaceEnum.YPLUS
            if direction[1] >= 0
            else _UnitCubeFaceEnum.YMINUS
        )

    return (
        _UnitCubeFaceEnum.ZPLUS
        if direction[2] >= 0
        else _UnitCubeFaceEnum.ZMINUS
    )


def _compute_uv_from_unitcube(point, face):
    """Compute UV coords from intersection point and face.

    The cube is unfold this way:

          +Z
    +X +Y -X -Y
          -Z

    """
    if face == _UnitCubeFaceEnum.XPLUS:
        res = App.Base.Vector2d(point[1], point[2])
    elif face == _UnitCubeFaceEnum.YPLUS:
        res = App.Base.Vector2d(-point[0] + 1.0, point[2])
    elif face == _UnitCubeFaceEnum.XMINUS:
        res = App.Base.Vector2d(-point[1] + 2.0, point[2])
    elif face == _UnitCubeFaceEnum.YMINUS:
        res = App.Base.Vector2d(point[0] + 3.0, point[2])
    elif face == _UnitCubeFaceEnum.ZPLUS:
        res = App.Base.Vector2d(point[0] + 2.0, point[1] + 1.0)
    elif face == _UnitCubeFaceEnum.ZMINUS:
        res = App.Base.Vector2d(point[0] + 2.0, -point[1] - 1.0)
    return res


# ===========================================================================
#                           Other uvmap helpers
# ===========================================================================


def _compute_barycenter(points):
    """Compute the barycenter of a list of points."""
    length = len(points)
    origin = App.Vector(0, 0, 0)
    if length == 0:
        return origin
    res = sum([p.Vector for p in points], origin) / length
    return res
