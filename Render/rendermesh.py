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

"""This module implements RenderMesh class.

RenderMesh is an extended version of FreeCAD Mesh.Mesh, designed for
rendering purpose.
"""

# Useful resources:
# https://www.pixyz-software.com/documentations/html/2021.1/studio/UVProjectionTool.html

import math
import enum
import os
import tempfile

import FreeCAD as App
import Mesh


class RenderMesh:
    """An extended version of FreeCAD Mesh, designed for rendering.

    RenderMesh is based on Mesh.Mesh and most of its API is common with
    the latter.
    In addition, RenderMesh implements UV map management.

    Please note that RenderMesh does not subclass Mesh.Mesh, as Mesh.Mesh is
    implemented in C, which prevents it to be subclassed in Python. As a
    workaround, the required methods and attributes are explicitly
    reimplemented as calls to the corresponding methods and attributes of
    Mesh.Mesh.
    """

    def __init__(self, mesh=None, uvmap=None, placement=App.Base.Placement()):
        """Initialize RenderMesh.

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
        return RenderMesh(self.__mesh.copy(), self.__uvmap)

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
        return iter(self.__mesh.Points)

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
    def write_objfile(
        self,
        name,
        objfile=None,
        mtlfile=None,
        mtlname=None,
        mtlcontent=None,
        normals=True,
        uv_translate=App.Base.Vector2d(0.0, 0.0),
        uv_rotate=0.0,
        uv_scale=1.0,
    ):
        """Write an OBJ file from a mesh.

        Args:
            name -- Name of the mesh (str)
            objfile -- Name of the OBJ file (str). If None, the OBJ file is
              written in a temporary file, whose name is returned by the
              function.
            mtlfile -- MTL file name to reference in OBJ (optional) (str)
            mtlname -- Material name to reference in OBJ, must be defined in
              MTL file (optional) (str)
            mtlcontent -- MTL file content (optional) (str)
            normals -- Flag to control the writing of normals in the OBJ file
              (bool)
            uv_translate -- UV translation vector (App.Base.Vector2d)
            uv_rotate -- UV rotation angle in degrees (float)
            uv_scale -- UV scale factor (float)

        Returns: the name of file that the function wrote.
        """
        # Retrieve and normalize arguments
        normals = bool(normals)

        # Get obj file name
        if objfile is None:
            f_handle, objfile = tempfile.mkstemp(suffix=".obj", prefix="_")
            os.close(f_handle)
        else:
            objfile = str(objfile)

        # Initialize
        header = ["# Written by FreeCAD-Render"]

        # Mtl
        if mtlcontent is not None:
            # Write mtl file
            mtlfilename = RenderMesh.write_mtl(mtlname, mtlcontent, mtlfile)
            if os.path.dirname(mtlfilename) != os.path.dirname(objfile):
                raise ValueError(
                    "OBJ and MTL files shoud be in the same dir\n"
                    f"('{objfile}' versus '{mtlfilename}')"
                )
            mtlfilename = os.path.basename(mtlfilename)
            mtl = [f"mtllib {mtlfilename}", ""]
        else:
            mtl = []

        # Vertices
        verts = [p.Vector for p in self.Points]
        verts = [f"v {v.x} {v.y} {v.z}" for v in verts]
        verts.insert(0, "# Vertices")
        verts.append("")

        # UV
        if self.has_uvmap():
            # Translate, rotate, scale (optionally)
            uvs = self.transformed_uvmap(uv_translate, uv_rotate, uv_scale)
            # Format
            uvs = [f"vt {t.x} {t.y}" for t in uvs]
            uvs.insert(0, "# Texture coordinates")
            uvs.append("")
        else:
            uvs = []

        # Vertex normals
        if normals:
            norms = [f"vn {n.x} {n.y} {n.z}" for n in self.getPointNormals()]
            norms.insert(0, "# Vertex normals")
            norms.append("")
        else:
            norms = []

        # Object name
        objname = [f"o {name}"]
        if mtlname is not None:
            objname.append(f"usemtl {mtlname}")
        objname.append("")

        # Faces
        if normals and self.has_uvmap():
            mask = "{i}/{i}/{i}"
        elif not normals and self.has_uvmap():
            mask = "{i}/{i}"
        elif normals and not self.has_uvmap():
            mask = "{i}//{i}"
        else:
            mask = "{i}"

        faces = [
            map(lambda x: mask.format(i=x + 1), f) for f in self.Topology[1]
        ]
        faces = [" ".join(f) for f in faces]
        faces = [f"f {f}" for f in faces]
        faces.insert(0, "# Faces")

        res = header + mtl + verts + uvs + norms + objname + faces
        res = "\n".join(res)

        with open(objfile, "w", encoding="utf-8") as f:
            f.write(res)

        return objfile

    @staticmethod
    def write_mtl(name, mtlcontent, mtlfile=None):
        """Write a MTL file.

        MTL file is the companion of OBJ file, thus we keep this method in
        RenderMesh, although there is no need of 'self' to write the MTL...

        Args:
        name -- The material name, to be referenced in OBJ (str)
        mtlcontent -- The material content (str)
        mtlfile -- The mtl file name to write to. If None, a temp file is
          created. (str)

        Returns:
        The MTL file name
        """
        if mtlfile is None:
            f_handle, mtlfile = tempfile.mkstemp(suffix=".mtl", prefix="_")
            os.close(f_handle)

        # _write_material(name, material)
        with open(mtlfile, "w", encoding="utf-8") as f:
            f.write(f"newmtl {name}")
            f.write(mtlcontent)
        return mtlfile

    @property
    def uvmap(self):
        """Get mesh uv map."""
        return self.__uvmap

    def transformed_uvmap(self, translate, rotate, scale):
        """Returns a transformed uvmap.

        Args:
            translate -- Translation vector (App.Base.Vector2d)
            rotate -- Rotation angle in degrees (float)
            scale -- Scale factor (float)

        Returns: a transformed uvmap
        """
        rotate = float(rotate)
        scale = float(scale)
        rotate = math.radians(rotate)
        if self.has_uvmap():
            # Translate, rotate, scale (optionally)
            uvbase = self.uvmap
            if translate.x != 0.0 or translate.y != 0.0:
                uvbase = [v + translate for v in uvbase]
            if rotate != 0.0:
                cosr = math.cos(rotate)
                sinr = math.sin(rotate)
                uvbase = [
                    App.Base.Vector2d(
                        v.x * cosr - v.y * sinr, v.x * sinr + v.y * cosr
                    )
                    for v in uvbase
                ]
            if scale != 1.0:
                uvbase = [v * scale for v in uvbase]
        else:
            uvbase = []
        return uvbase

    def uvmap_per_vertex(self):
        """Get mesh uv map by vertex.

        (used in Cycles)
        """
        return [
            self.__uvmap[vertex_index]
            for triangle in self.__mesh.Topology[1]
            for vertex_index in triangle
        ]

    def compute_uvmap(self, projection):
        """Compute UV map for this mesh."""
        projection = "Cubic" if projection is None else projection
        if projection == "Cubic":
            self._compute_uvmap_cube()
        elif projection == "Spherical":
            self._compute_uvmap_sphere()
        elif projection == "Cylindric":
            self._compute_uvmap_cylinder()
        else:
            raise ValueError

    def _compute_uvmap_cylinder(self):
        """Compute UV map for cylindric case.

        Cylinder axis is supposed to be z.
        """
        # Split mesh into 3 submeshes:
        # non z-normal facets, not on seam (regular)
        # non z-normal facets, on seam (seam)
        # z-normal facets
        regular, seam, znormal = [], [], []
        z_vector = App.Base.Vector(0.0, 0.0, 1.0)
        for facet in self.__originalmesh.Facets:
            if _is_facet_normal_to_vector(facet, z_vector):
                znormal.append(facet)
            elif _facet_overlap_seam(facet):
                seam.append(facet)
            else:
                regular.append(facet)

        # Rebuild a complete mesh from submeshes, with uvmap
        mesh = Mesh.Mesh()
        uvmap = []

        # Non Z-normal facets (regular)
        regular_mesh = Mesh.Mesh(regular)
        points = list(regular_mesh.Points)
        avg_radius = sum(math.hypot(p.x, p.y) for p in points) / len(points)
        uvmap += [
            App.Base.Vector2d(math.atan2(p.x, p.y) * avg_radius, p.z) * 0.001
            for p in points
        ]
        regular_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(regular_mesh)

        # Non Z-normal facets (seam)
        seam_mesh = Mesh.Mesh(seam)
        points = list(seam_mesh.Points)
        avg_radius = (
            sum(math.hypot(p.x, p.y) for p in points) / len(points)
            if points
            else 0
        )
        uvmap += [
            App.Base.Vector2d(_pos_atan2(p.x, p.y) * avg_radius, p.z) * 0.001
            for p in points
        ]
        seam_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(seam_mesh)

        # Z-normal facets
        z_mesh = Mesh.Mesh(znormal)
        uvmap += [
            App.Base.Vector2d(p.x / 1000, p.y / 1000)
            for p in list(z_mesh.Points)
        ]
        z_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(z_mesh)

        # Replace previous values with newly computed ones
        self.__mesh = mesh
        self.__uvmap = tuple(uvmap)

    def _compute_uvmap_sphere(self):
        """Compute UV map for spherical case."""
        # Split mesh into 2 submeshes:
        # - facets not on seam (regular)
        # - facets on seam (seam)
        regular, seam = [], []
        for facet in self.__originalmesh.Facets:
            if _facet_overlap_seam(facet):
                seam.append(facet)
            else:
                regular.append(facet)

        # Rebuild a complete mesh from submeshes, with uvmap
        mesh = Mesh.Mesh()
        uvmap = []
        origin = _compute_barycenter(self.__originalmesh.Points)

        # Regular facets
        regular_mesh = Mesh.Mesh(regular)
        vectors = [p.Vector - origin for p in list(regular_mesh.Points)]
        uvmap += [
            App.Base.Vector2d(
                0.5 + math.atan2(v.x, v.y) / (2 * math.pi),
                0.5 + math.asin(v.z / v.Length) / math.pi,
            )
            * (v.Length / 1000.0 * math.pi)
            for v in vectors
        ]
        regular_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(regular_mesh)

        # Seam facets
        seam_mesh = Mesh.Mesh(seam)
        vectors = [p.Vector - origin for p in list(seam_mesh.Points)]
        uvmap += [
            App.Base.Vector2d(
                0.5 + _pos_atan2(v.x, v.y) / (2 * math.pi),
                0.5 + math.asin(v.z / v.Length) / math.pi,
            )
            * (v.Length / 1000.0 * math.pi)
            for v in vectors
        ]
        seam_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(seam_mesh)

        # Replace previous values with newly computed ones
        self.__mesh = mesh
        self.__uvmap = tuple(uvmap)

    def _compute_uvmap_cube(self):
        """Compute UV map for cubic case.

        We isolate submeshes by cube face in order to avoid trouble when
        one edge belongs to several cube faces (cf. simple cube case, for
        instance)
        """
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
        res = App.Base.Vector2d(-point[0], point[2])
    elif face == _UnitCubeFaceEnum.XMINUS:
        res = App.Base.Vector2d(-point[1], point[2])
    elif face == _UnitCubeFaceEnum.YMINUS:
        res = App.Base.Vector2d(point[0], point[2])
    elif face == _UnitCubeFaceEnum.ZPLUS:
        res = App.Base.Vector2d(point[0], point[1])
    elif face == _UnitCubeFaceEnum.ZMINUS:
        res = App.Base.Vector2d(point[0], -point[1])
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


def _is_facet_normal_to_vector(facet, vector):
    """Test whether a facet is normal to a vector.

    math.isclose is used to assess dot product nullity.
    """
    pt1, pt2, pt3 = facet.Points
    vec1 = (App.Base.Vector(*pt2) - App.Base.Vector(*pt1)).normalize()
    vec2 = (App.Base.Vector(*pt3) - App.Base.Vector(*pt1)).normalize()
    vector = vector.normalize()
    tolerance = 1e-5
    res = math.isclose(
        vec1.dot(vector), 0.0, abs_tol=tolerance
    ) and math.isclose(vec2.dot(vector), 0.0, abs_tol=tolerance)
    return res


def _facet_overlap_seam(facet):
    """Test whether facet overlaps the seam."""
    phis = [math.atan2(x, y) for x, y, _ in facet.Points]
    return max(phis) * min(phis) < 0


def _pos_atan2(p_x, p_y):
    """Wrap atan2 to get only positive values (seam treatment)."""
    atan2 = math.atan2(p_x, p_y)
    return atan2 if atan2 >= 0 else atan2 + 2 * math.pi
