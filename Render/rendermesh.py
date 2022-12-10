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

import enum
import os
import tempfile
import operator
import itertools as it
import functools
import time  # TODO
from math import pi, atan2, asin, isclose, radians, degrees, cos, sin, hypot
from collections import namedtuple
import runpy

import FreeCAD as App
import Mesh

from Render.constants import PKGDIR

Vector2d = namedtuple("Vector2d", "x y")


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

    def __init__(
        self,
        mesh=None,
        uvmap=None,
        normals=None,
        placement=App.Base.Placement(),
    ):
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
            self.__normals = (
                normals
                if normals is not None
                else list(self.__mesh.getPointNormals())
            )
        else:
            self.__mesh = Mesh.Mesh()
            self.__normals = []
        self.__uvmap = uvmap if bool(uvmap) else []

    # Reexposed Mesh.Mesh methods and attributes
    def __repr__(self):
        """Give a printable representation of the object."""
        return self.__mesh.__repr__()

    def addFacet(self, *args):  # pylint: disable=invalid-name
        """Add a facet to the mesh."""
        self.__mesh.addFacet(*args)

    def copy(self):
        """Creates a copy of this mesh."""
        return RenderMesh(
            mesh=self.__mesh.copy(),
            uvmap=self.__uvmap.copy(),
            normals=self.__normals.copy(),
        )

    def getPointNormals(self):  # pylint: disable=invalid-name
        """Get the normals for each point."""
        return self.__normals

    def harmonizeNormals(self):  # pylint: disable=invalid-name
        """Adjust wrong oriented facets."""
        self.__mesh.harmonizeNormals()

    def rotate(self, angle_x, angle_y, angle_z):
        """Apply a rotation to the mesh.

        Args:
            angle_x, angle_y, angle_z -- angles in radians
        """
        self.__mesh.rotate(angle_x, angle_y, angle_z)
        rotation = App.Base.Rotation(
            degrees(angle_z), degrees(angle_y), degrees(angle_x)
        )
        self.__normals = [rotation.multVec(v) for v in self.__normals]

    def transform(self, matrix):
        """Apply a transformation to the mesh."""
        self.__mesh.transform(matrix)
        self.__normals = [matrix.multVec(v) for v in self.__normals]
        self.__normals = [
            v / v.Length for v in self.__normals if v.Length != 0.0
        ]

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
    def Facets(self):  # pylint: disable=invalid-name
        """Get a collection of the mesh points.

        WARNING! Store Facets in a local variable as it is generated on the
        fly, each time it is accessed.
        """
        return iter(self.__mesh.Facets)

    @property
    def Topology(self):  # pylint: disable=invalid-name
        """Get the points and faces indices as tuples.

        Topology[0] is a list of all vertices. Each being a tuple of 3
        coordinates. Topology[1] is a list of all polygons. Each being a list
        of vertex indices into Topology[0]

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
        uv_translate=Vector2d(0.0, 0.0),
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
            uv_translate -- UV translation vector (Vector2d)
            uv_rotate -- UV rotation angle in degrees (float)
            uv_scale -- UV scale factor (float)

        Returns: the name of file that the function wrote.
        """
        t = time.time()
        # Retrieve and normalize arguments
        normals = bool(normals)

        # Initialize
        vertices, indices = self.Topology  # Time consuming...
        nverts = len(vertices)
        ninds = len(indices)


        # Get obj file name
        if objfile is None:
            f_handle, objfile = tempfile.mkstemp(suffix=".obj", prefix="_")
            os.close(f_handle)
        else:
            objfile = str(objfile)

        # Header
        header = ["# Written by FreeCAD-Render\n"]

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
            mtl = [f"mtllib {mtlfilename}\n\n"]
        else:
            mtl = []

        # Vertices
        if nverts < 1000:
            fmtv = functools.partial(str.format, "v {} {} {}\n")
            verts = (fmtv(*v) for v in vertices)
        else:
            verts_tuples = [tuple(v) for v in vertices]
            path = os.path.join(PKGDIR, "testmulti.py")
            res = runpy.run_path(
                path,
                init_globals={"values": verts_tuples, "fmt": "v", "length": nverts},
                run_name="__main__",
            )
            verts = res["result"]
        verts = it.chain(["# Vertices\n"], verts, ["\n"])

        # UV
        if self.has_uvmap():
            # Translate, rotate, scale (optionally)
            uvs = uvtransform(self.uvmap, uv_translate, uv_rotate, uv_scale)
            if nverts < 1000:
                fmtuv = functools.partial(str.format, "vt {} {}\n")
                uvs = (fmtuv(*t) for t in uvs)
            else:
                res = runpy.run_path(
                    path,
                    init_globals={"values": list(uvs), "fmt": "vt", "length": ninds},
                    run_name="__main__",
                )
                uvs = res["result"]
            uvs = it.chain(["# Texture coordinates\n"], uvs, "\n")
        else:
            uvs = []

        # Vertex normals
        if normals:
            norms = self.__normals
            fmtn = functools.partial(str.format, "vn {} {} {}\n")
            norms = (fmtn(*n) for n in norms)
            norms = it.chain(["# Vertex normals\n"], norms, "\n")
        else:
            norms = []

        # Object name
        objname = [f"o {name}\n"]
        if mtlname is not None:
            objname.append(f"usemtl {mtlname}\n")
        objname.append("\n")

        # Faces
        if normals and self.has_uvmap():
            mask = " {0}/{0}/{0}"
        elif not normals and self.has_uvmap():
            mask = " {0}/{0}"
        elif normals and not self.has_uvmap():
            mask = " {0}//{0}"
        else:
            mask = " {}"

        if nverts < 1000:
            fmtf = functools.partial(str.format, mask)
            joinf = functools.partial(str.join, "")

            faces = (
                joinf(["f"] + [fmtf(x + 1) for x in f] + ["\n"]) for f in indices
            )
        else:
            res = runpy.run_path(
                path,
                init_globals={"values": indices, "fmt": "f", "length": ninds, "mask": mask},
                run_name="__main__",
            )
            faces = res["result"]

        faces = it.chain(["# Faces\n"], faces)

        res = it.chain(header, mtl, verts, uvs, norms, objname, faces)

        with open(objfile, "w", encoding="utf-8") as f:
            f.writelines(res)

        print("write_objfile", time.time() - t)
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
            f.write(f"newmtl {name}\n")
            f.write(mtlcontent)
        return mtlfile

    @property
    def uvmap(self):
        """Get mesh uv map."""
        return self.__uvmap

    def transformed_uvmap(self, translate, rotate, scale):
        """Returns a transformed uvmap.

        Args:
            translate -- Translation vector (Vector2d)
            rotate -- Rotation angle in degrees (float)
            scale -- Scale factor (float)

        Returns: a transformed uvmap
        """
        rotate = float(rotate)
        scale = float(scale)
        rotate = radians(rotate)
        if self.has_uvmap():
            # Translate, rotate, scale (optionally)
            uvbase = self.uvmap
            if translate.x != 0.0 or translate.y != 0.0:
                uvbase = [
                    (v.x + translate.x, v.y + translate.y) for v in uvbase
                ]
            if rotate != 0.0:
                cosr = cos(rotate)
                sinr = sin(rotate)
                uvbase = [
                    Vector2d(v.x * cosr - v.y * sinr, v.x * sinr + v.y * cosr)
                    for v in uvbase
                ]
            if scale != 1.0:
                uvbase = [(v.x * scale, v.y * scale) for v in uvbase]
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

    def center_of_gravity(self):
        """Get mesh's center of gravity.

        Mesh CoG is the barycenter of the facets CoG, weighted by facets
        areas
        """
        mesh = self.__originalmesh
        vec0 = App.Vector(0, 0, 0)

        facets = ([App.Vector(p) for p in f.Points] for f in mesh.Facets)
        facetbars = [sum(f, vec0) / len(f) for f in facets]
        areas = [f.Area for f in mesh.Facets]
        cog = sum(map(operator.mul, facetbars, areas), vec0) / sum(areas)
        return cog

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
        self.compute_normals()

    def compute_normals(self):
        """Compute point normals.

        Refresh self._normals.
        """
        mesh = self.__mesh

        norms = [App.Base.Vector()] * mesh.CountPoints
        for facet in mesh.Facets:
            weighted_norm = facet.Normal * facet.Area
            for index in facet.PointIndices:
                norms[index] += weighted_norm
        for norm in norms:
            norm.normalize()
        self.__normals = norms

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
        avg_radius = sum(hypot(p.x, p.y) for p in points) / len(points)
        uvmap += [
            Vector2d(atan2(p.x, p.y) * avg_radius, p.z) * 0.001
            for p in points
        ]
        regular_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(regular_mesh)

        # Non Z-normal facets (seam)
        seam_mesh = Mesh.Mesh(seam)
        points = list(seam_mesh.Points)
        avg_radius = (
            sum(hypot(p.x, p.y) for p in points) / len(points)
            if points
            else 0
        )
        uvmap += [
            Vector2d(_pos_atan2(p.x, p.y) * avg_radius, p.z) * 0.001
            for p in points
        ]
        seam_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(seam_mesh)

        # Z-normal facets
        z_mesh = Mesh.Mesh(znormal)
        uvmap += [
            Vector2d(p.x / 1000, p.y / 1000) for p in list(z_mesh.Points)
        ]
        z_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(z_mesh)

        # Replace previous values with newly computed ones
        self.__mesh = mesh
        self.__uvmap = uvmap

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
        try:
            origin = self.__originalmesh.CenterOfGravity
        except AttributeError:
            origin = self.center_of_gravity()

        # Regular facets
        regular_mesh = Mesh.Mesh(regular)
        vectors = [p.Vector - origin for p in list(regular_mesh.Points)]
        uvmap += [
            Vector2d(
                (0.5 + atan2(v.x, v.y) / (2 * pi)) * (v.Length / 1000.0 * pi),
                (0.5 + asin(v.z / v.Length) / pi) * (v.Length / 1000.0 * pi),
            )
            for v in vectors
        ]
        regular_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(regular_mesh)

        # Seam facets
        seam_mesh = Mesh.Mesh(seam)
        vectors = [p.Vector - origin for p in list(seam_mesh.Points)]
        uvmap += [
            Vector2d(
                (0.5 + _pos_atan2(v.x, v.y) / (2 * pi))
                * (v.Length / 1000.0 * pi),
                (0.5 + asin(v.z / v.Length) / pi) * (v.Length / 1000.0 * pi),
            )
            for v in vectors
        ]
        seam_mesh.transform(self.__originalplacement.Matrix)
        mesh.addMesh(seam_mesh)

        # Replace previous values with newly computed ones
        self.__mesh = mesh
        self.__uvmap = uvmap

    def _compute_uvmap_cube(self):
        """Compute UV map for cubic case.

        We isolate submeshes by cube face in order to avoid trouble when
        one edge belongs to several cube faces (cf. simple cube case, for
        instance)
        """
        # Isolate submeshes by cube face
        face_facets = ([], [], [], [], [], [])
        for facet in self.__originalmesh.Facets:
            cubeface = _intersect_unitcube_face(facet.Normal)
            # Add facet to corresponding submesh
            face_facets[cubeface].append(facet)

        # Rebuid a complete mesh from face submeshes, with uvmap
        uvmap = []
        mesh = Mesh.Mesh()
        try:
            cog = self.__originalmesh.CenterOfGravity
        except AttributeError:
            cog = self.center_of_gravity()
        transmat = self.__originalplacement.Matrix
        for cubeface, facets in enumerate(face_facets):
            facemesh = Mesh.Mesh(facets)
            # Compute uvmap of the submesh
            facemesh_uvmap = [
                _compute_uv_from_unitcube((p.Vector - cog) / 1000, cubeface)
                # pylint: disable=not-an-iterable
                for p in facemesh.Points
            ]
            # Add submesh and uvmap
            facemesh.transform(transmat)
            mesh.addMesh(facemesh)
            uvmap += facemesh_uvmap

        # Replace previous values with newly computed ones
        self.__mesh = mesh
        self.__uvmap = uvmap

    def has_uvmap(self):
        """Check if object has a uv map."""
        return bool(self.__uvmap)


# ===========================================================================
#                           Cube uvmap helpers
# ===========================================================================


class _UnitCubeFaceEnum(enum.IntEnum):
    """A class to describe a face of a unit cube.

    A unit cube is cube centered on the origin, each face perpendicular to one
    of the axes of the reference frame and the distance from the origin to each
    face being equal to 1.
    This cube is useful for projections for uv map...
    """

    XPLUS = 0
    XMINUS = 1
    YPLUS = 2
    YMINUS = 3
    ZPLUS = 4
    ZMINUS = 5


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
    dirx, diry, dirz = direction
    dabsx, dabsy, dabsz = abs(dirx), abs(diry), abs(dirz)

    if dabsx >= dabsy and dabsx >= dabsz:
        return (
            0  # _UnitCubeFaceEnum.XPLUS
            if dirx >= 0
            else 1  # _UnitCubeFaceEnum.XMINUS
        )

    if dabsy >= dabsx and dabsy >= dabsz:
        return (
            2  # _UnitCubeFaceEnum.YPLUS
            if diry >= 0
            else 3  # _UnitCubeFaceEnum.YMINUS
        )

    return (
        4  # _UnitCubeFaceEnum.ZPLUS
        if dirz >= 0
        else 5  # _UnitCubeFaceEnum.ZMINUS
    )


def _compute_uv_from_unitcube(point, face):
    """Compute UV coords from intersection point and face.

    The cube is unfold this way:

          +Z
    +X +Y -X -Y
          -Z

    """
    pt0, pt1, pt2 = point
    if face == 0:  # _UnitCubeFaceEnum.XPLUS
        res = Vector2d(pt1, pt2)
    elif face == 1:  # _UnitCubeFaceEnum.XMINUS
        res = Vector2d(-pt1, pt2)
    elif face == 2:  # _UnitCubeFaceEnum.YPLUS
        res = Vector2d(-pt0, pt2)
    elif face == 3:  # _UnitCubeFaceEnum.YMINUS
        res = Vector2d(pt0, pt2)
    elif face == 4:  # _UnitCubeFaceEnum.ZPLUS
        res = Vector2d(pt0, pt1)
    elif face == 5:  # _UnitCubeFaceEnum.ZMINUS
        res = Vector2d(pt0, -pt1)
    return res


# ===========================================================================
#                           Other uvmap helpers
# ===========================================================================


def _is_facet_normal_to_vector(facet, vector):
    """Test whether a facet is normal to a vector.

    math.isclose is used to assess dot product nullity.
    """
    pt1, pt2, pt3 = facet.Points
    vec1 = (App.Base.Vector(*pt2) - App.Base.Vector(*pt1)).normalize()
    vec2 = (App.Base.Vector(*pt3) - App.Base.Vector(*pt1)).normalize()
    vector = vector.normalize()
    tolerance = 1e-5
    res = isclose(vec1.dot(vector), 0.0, abs_tol=tolerance) and isclose(
        vec2.dot(vector), 0.0, abs_tol=tolerance
    )
    return res


def _facet_overlap_seam(facet):
    """Test whether facet overlaps the seam."""
    phis = [atan2(x, y) for x, y, _ in facet.Points]
    return max(phis) * min(phis) < 0


def _pos_atan2(p_x, p_y):
    """Wrap atan2 to get only positive values (seam treatment)."""
    atan2_xy = atan2(p_x, p_y)
    return atan2_xy if atan2_xy >= 0 else atan2_xy + 2 * pi


def uvtransform(uvmap, translate, rotate, scale):
    """Compute a uv transformation (iterator).

    Args:
        uvmap -- the uv map to transform
        translate -- Translation vector (Vector2d)
        rotate -- Rotation angle in degrees (float)
        scale -- Scale factor (float)
    """
    trans_x, trans_y = translate

    scale = float(scale)

    rotate = radians(float(rotate))

    def _000():
        """Nop."""
        return iter(uvmap)

    def _00t():
        """Translate."""
        return (Vector2d(vec.x + trans_x, vec.y + trans_y) for vec in uvmap)

    def _0s0():
        """Scale."""
        return (Vector2d(vec.x * scale, vec.y * scale) for vec in uvmap)

    def _0st():
        """Scale, translate."""
        return (
            Vector2d(vec.x * scale + trans_x, vec.y * scale + trans_y)
            for vec in uvmap
        )

    def _r00():
        """Rotate."""
        cosr = cos(rotate)
        sinr = sin(rotate)
        return (
            Vector2d(
                vec.x * cosr - vec.y * sinr,
                vec.x * sinr + vec.y * cosr,
            )
            for vec in uvmap
        )

    def _r0t():
        """Rotate, translate."""
        cosr = cos(rotate)
        sinr = sin(rotate)
        return (
            Vector2d(
                vec.x * cosr - vec.y * sinr + trans_x,
                vec.x * sinr + vec.y * cosr + trans_y,
            )
            for vec in uvmap
        )

    def _rs0():
        """Rotate, scale."""
        cosrs = cos(rotate) * scale
        sinrs = sin(rotate) * scale
        return (
            Vector2d(
                vec.x * cosrs - vec.y * sinrs,
                vec.x * sinrs + vec.y * cosrs,
            )
            for vec in uvmap
        )

    def _rst():
        """Rotate, scale, translate."""
        cosrs = cos(rotate) * scale
        sinrs = sin(rotate) * scale
        return (
            Vector2d(
                vec.x * cosrs - vec.y * sinrs + trans_x,
                vec.x * sinrs + vec.y * cosrs + trans_y,
            )
            for vec in uvmap
        )

    # Select and return the right function
    index = (
        rotate != 0.0,
        scale != 1.0,
        trans_x != 0.0 or trans_y != 0.0,
    )
    index = sum(it.compress((4, 2, 1), index))
    functions = (_000, _00t, _0s0, _0st, _r00, _r0t, _rs0, _rst)
    return functions[index]()
