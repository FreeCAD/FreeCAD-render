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
        points = self.Points
        barycenter = compute_barycenter(points)
        # TODO Should center be barycenter or boundingbox center?
        vectors = [(p.Vector - barycenter).normalize() for p in points]
        # TODO determine optimal signature for _compute_uvmap_*
        # self._compute_uvmap_sphere(points, barycenter, vectors)
        self._compute_uvmap_cube(points, barycenter, vectors)

    # TODO
    # Useful resources: https://www.pixyz-software.com/documentations/html/2021.1/studio/UVProjectionTool.html

    def _compute_uvmap_sphere(self, points, barycenter, vectors):
        """Compute UV map for spherical case."""
        self.__uvmap = tuple(
            App.Base.Vector2d(
                0.5 + math.atan2(v.x, v.y) / (2 * math.pi),
                0.5 + math.asin(v.z) / math.pi,
            )
            for v in vectors
        )

    # TODO Remove
    # def _compute_uvmap_cube(self, points, barycenter, vectors):
        # """Compute UV map for cubic case."""
        # res = []
        # for vec in vectors:
            # # Determine which face is intersected
            # face = _intersect_unitcube_face(vec)
            # # Determine intersection point
            # point = _intersect_unitcube_point(vec, face)
            # # Determine uv
            # uvcoord = _compute_uv_from_unitcube(point, face)
            # res.append(uvcoord)
        # self.__uvmap = tuple(res)

    def _compute_uvmap_cube(self, points, barycenter, vectors):
        # TODO Docstring
        # Sort facets by cube face
        facemeshes = {f: Mesh.Mesh() for f in UnitCubeFaceEnum}
        for facet in self.__mesh.Facets:
            # Determine which cubeface the facet belongs to
            facet_center = facet.InCircle[0]
            direction = facet_center - barycenter
            cubeface = _intersect_unitcube_face(direction)
            # Add facet to corresponding submesh
            facemeshes[cubeface].addFacet(facet)

        # Rebuid a complete mesh from face meshes
        uvmap = []
        mesh = Mesh.Mesh()
        mesh.Placement = self.Placement
        for cubeface, facemesh in facemeshes.items():
            facemesh.optimizeTopology()
            # Compute uvmap of the submesh
            facemesh_uvmap = []
            for point in facemesh.Points:
                point2 = point.Vector - barycenter
                intersect_point = _intersect_unitcube_point(point2, cubeface)
                uvcoord = _compute_uv_from_unitcube(intersect_point, cubeface)
                facemesh_uvmap.append(uvcoord)
            # Add submesh and uvmap
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

class UnitCubeFaceEnum(enum.Enum):
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
UNIT_CUBE_FACES_NORMALS = {
    UnitCubeFaceEnum.XPLUS: (1.0, 0.0, 0.0),
    UnitCubeFaceEnum.XMINUS: (-1.0, 0.0, 0.0),
    UnitCubeFaceEnum.YPLUS: (0.0, 1.0, 0.0),
    UnitCubeFaceEnum.YMINUS: (0.0, -1.0, 0.0),
    UnitCubeFaceEnum.ZPLUS: (0.0, 0.0, 1.0),
    UnitCubeFaceEnum.ZMINUS: (0.0, 0.0, -1.0),
}


def _intersect_unitcube_point(direction, cubeface):
    """Get the intersection btw a line from the origin and a face of a unit cube.

    Args:
        direction -- a 3-tuple representing the directing vector of a line crossing
        the origin
        cubeface -- the unit cube face to be intersected (UnitCubeFaceEnum)

    Returns:
        The intersection point (3-tuple)

    Rem: We solve the following system in (x, y, z, t):
      cubeface[0].x + cubeface[1].y + cubeface[2].z = 1
      x = direction[0].t
      y = direction[1].t
      z = direction[2].t
    """
    face_normal = UNIT_CUBE_FACES_NORMALS[cubeface]
    det = sum(a * b for a, b in zip(direction, face_normal))
    if det == 0.0:
        raise ValueError
    return tuple(d / det for d in direction)


def _intersect_unitcube_face(direction):
    """Get the face of the unit cube intersected by a line from origin.

    Args:
        direction -- The directing vector for the intersection line
        (a 3-float sequence)

    Returns:
        A face from the unit cube (UnitCubeFaceEnum)
    """
    dabs = (abs(direction[0]), abs(direction[1]), abs(direction[2]))

    if dabs[0] >= dabs[1] and dabs[0] >= dabs[2]:
        return (
            UnitCubeFaceEnum.XPLUS
            if direction[0] >= 0
            else UnitCubeFaceEnum.XMINUS
        )

    if dabs[1] >= dabs[0] and dabs[1] >= dabs[2]:
        return (
            UnitCubeFaceEnum.YPLUS
            if direction[1] >= 0
            else UnitCubeFaceEnum.YMINUS
        )

    return (
        UnitCubeFaceEnum.ZPLUS
        if direction[2] >= 0
        else UnitCubeFaceEnum.ZMINUS
    )


def _compute_uv_from_unitcube(point, face):
    """Compute UV coords from intersection point and face.
    
    The cube is unfold this way:
    
          +Z
    +X +Y -X -Y
          -Z

    """
    # TODO
    if face == UnitCubeFaceEnum.XPLUS:
        res = App.Base.Vector2d(point[1], point[2])
    elif face == UnitCubeFaceEnum.YPLUS:
        res = App.Base.Vector2d(-point[0] + 1.0, point[2])
    elif face == UnitCubeFaceEnum.XMINUS:
        res = App.Base.Vector2d(-point[1] + 2.0, point[2])
    elif face == UnitCubeFaceEnum.YMINUS:
        res = App.Base.Vector2d(point[0] + 3.0, point[2])
    elif face == UnitCubeFaceEnum.ZPLUS:
        res = App.Base.Vector2d(point[0] + 2.0, point[1] + 1.0)
    elif face == UnitCubeFaceEnum.ZMINUS:
        res = App.Base.Vector2d(point[0] + 2.0, -point[1] - 1.0)
    return res


# ===========================================================================
#                           Other uvmap helpers
# ===========================================================================

def compute_barycenter(points):
    """Compute the barycenter of a list of points."""
    length = len(points)
    origin = App.Vector(0, 0, 0)
    if length == 0:
        return origin
    res = sum([p.Vector for p in points], origin) / length
    return res
