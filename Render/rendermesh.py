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

"""This module implements RenderMesh class.

RenderMesh is an extended version of FreeCAD Mesh.Mesh, designed for
rendering purpose.
"""

# Useful resources:
# https://www.pixyz-software.com/documentations/html/2021.1/studio/UVProjectionTool.html

import enum
import os
import tempfile
import itertools as it
import functools
import time
from math import pi, atan2, asin, isclose, radians, cos, sin, hypot
import runpy
import shutil
import copy
import multiprocessing as mp

import FreeCAD as App
import Mesh

from Render.constants import PKGDIR, PARAMS
from Render.rendermesh_mp import vector3d
from Render.utils import warn, debug, grouper, SharedWrapper

try:
    mp.set_start_method("spawn")
except RuntimeError:
    # Already set...
    pass

try:
    import numpy as np

    USE_NUMPY = True
except ModuleNotFoundError:
    USE_NUMPY = False


# ===========================================================================
#                             RenderMesh factory
# ===========================================================================


def create_rendermesh(
        mesh,
        autosmooth=True,
        split_angle=radians(30),
        compute_uvmap=False,
        uvmap_projection=None,
        project_directory=None,
        export_directory=None,
        relative_path=True,
        skip_meshing=False,
        name="",
):
    RenderMesh = type("RenderMesh", (RenderMeshBase,), {})
    instance = RenderMesh(
        mesh,
        autosmooth,
        split_angle,
        compute_uvmap,
        uvmap_projection,
        project_directory,
        export_directory,
        relative_path,
        skip_meshing,
        name="",
    )
    return instance


# ===========================================================================
#                               RenderMesh
# ===========================================================================


class RenderMeshBase:
    """An extended version of FreeCAD Mesh, designed for rendering.

    RenderMesh is based on Mesh.Mesh.
    In addition, RenderMesh implements:
    - UV map management
    - scaling, via _Transformation
    - an improved vertex normals computation, for autosmoothing
    """

    def __init__(
        self,
        mesh,
        autosmooth=True,
        split_angle=radians(30),
        compute_uvmap=False,
        uvmap_projection=None,
        project_directory=None,
        export_directory=None,
        relative_path=True,
        skip_meshing=False,
        name="",
    ):
        """Initialize RenderMesh.

        Args:
            mesh -- a Mesh.Mesh object from which to initialize
            autosmooth -- flag to trigger autosmooth computation (bool)
            split_angle -- angle that breaks adjacency, for sharp edge
                (float, in radians)
            compute_uvmap -- flag to trigger uvmap computation (bool)
            uvmap_projection -- type of projection to use for uv map
                among "Cubic", "Spherical", "Cylindric"
            export_directory -- directory where the mesh is to be exported
            project_directory -- directory where the rendering project lays
            relative_path -- flag to control whether returned path is relative
                or absolute to project_directory
        """
        # Directories, for write methods
        self.export_directory = _check_directory(export_directory)
        self.project_directory = _check_directory(project_directory)
        self.relative_path = bool(relative_path)

        # We initialize self transformation
        self.__transformation = _Transformation(mesh.Placement)

        # Skip meshing?
        self.skip_meshing = bool(skip_meshing)
        if self.skip_meshing:
            self.__points = []
            self.__facets = []
            return

        # Check mandatory input
        if not mesh:
            raise ValueError()

        self.name = name

        # Initialize
        self.__vnormals = []
        self.__uvmap = []

        # First we make a copy of the mesh, we separate mesh and
        # placement and we set the mesh at its origin (null placement)
        self.__originalmesh = mesh
        self.__originalmesh.Placement = App.Base.Placement()

        # Then we store the topology in internal structures
        points, facets = self.__originalmesh.Topology
        self.__points = [tuple(p) for p in points]
        self.__facets = facets
        self.__normals = [tuple(f.Normal) for f in self.__originalmesh.Facets]
        self.__areas = [f.Area for f in self.__originalmesh.Facets]

        # Multiprocessing preparation (if required)
        self.multiprocessing = False
        if (
            PARAMS.GetBool("EnableMultiprocessing")
            and self.count_points >= 2000
        ):
            python = _find_python()
            if python:
                self.multiprocessing = True
                self.python = python

        # Sanity check
        if not facets:
            warn("Object", self.name, "Warning - Empty mesh (no facet)")
            return

        # Uvmap
        if compute_uvmap:
            msg = f"Uv map '{uvmap_projection}'"
            debug("Object", self.name, msg)
            self.compute_uvmap(uvmap_projection)
            assert self.has_uvmap()

        # Autosmooth
        if autosmooth:
            debug("Object", self.name, "Autosmooth")
            self.separate_connected_components(split_angle)
            self.compute_vnormals()
            self.__autosmooth = True
        else:
            self.__autosmooth = False

    def __del__(self):
        """Finalize RenderMesh.

        In particular, we clear and del the original Mesh.Mesh object (copy),
        to avoid memory leaks.
        """
        # Clean original mesh
        self.__originalmesh.clear()
        self.__originalmesh = None

        # # Debug memory:
        # import gc
        # import reprlib
        # myrepr = reprlib.Repr()
        # myrepr.maxdict = 50
        # for e in gc.get_referrers(self.__points):
        # print(myrepr.repr(e))

    ##########################################################################
    #                               Copy                                     #
    ##########################################################################

    def copy(self):
        """Creates a copy of this mesh."""
        # Caveat: this is a shallow copy!
        # In particular, we don't copy the __originalmesh (Mesh.Mesh)
        # So we point on the same object, which should not be modified
        new_mesh = copy.copy(self)
        # pylint: disable=protected-access, unused-private-member
        new_mesh.__transformation = copy.copy(self.transformation)
        return new_mesh

    ##########################################################################
    #                               Getters                                  #
    ##########################################################################

    @property
    def transformation(self):
        """Get the mesh transformation."""
        return self.__transformation

    @property
    def points(self):
        """Get a collection of the mesh points."""
        return self.__points

    @property
    def count_points(self):
        """Get the number of points."""
        return len(self.__points)

    @property
    def facets(self):
        """Get a collection of the mesh facets."""
        return self.__facets

    @property
    def count_facets(self):
        """Get the number of facets."""
        return len(self.__facets)

    @property
    def vnormals(self):
        """Get the vertex normals (if computed)."""
        return self.__vnormals

    @property
    def autosmooth(self):
        """Get the smoothness state of the mesh (boolean)."""
        return self.__autosmooth

    def has_uvmap(self):
        """Check if object has a uv map."""
        return bool(self.__uvmap)

    def has_vnormals(self):
        """Check if object has a vertex normals."""
        return bool(self.__vnormals)

    ##########################################################################
    #                               Write functions                          #
    ##########################################################################

    class ExportType(enum.IntEnum):
        """File types for mesh export."""

        OBJ = enum.auto()
        PLY = enum.auto()
        CYCLES = enum.auto()
        POVRAY = enum.auto()

    def write_file(
        self,
        name,
        filetype,
        filename=None,
        uv_translate=(0.0, 0.0),
        uv_rotate=0.0,
        uv_scale=1.0,
        **kwargs,
    ):
        """Export a mesh as a file.

        Args:
            name -- Name of the mesh (str)
            filetype -- The type of the file to write (Rendermesh.ExportType)
            filename -- The name of the file (str). If None, the file is
              written in a temporary file, whose name is returned by the
              function.
            uv_translate -- UV translation vector (2-uple)
            uv_rotate -- UV rotation angle in degrees (float)
            uv_scale -- UV scale factor (float)

        Keyword args:
            mtlfile -- MTL file name to reference in OBJ (optional) (str)
            mtlname -- Material name to reference in OBJ, must be defined in
              MTL file (optional) (str)
            mtlcontent -- MTL file content (optional) (str)

        Returns:
            The name of file that the function wrote.
        """
        # Normalize arguments
        filetype = RenderMeshBase.ExportType(filetype)

        # Compute target file
        if filename is None:
            export_directory = (
                self.export_directory
                if self.export_directory is not None
                else App.ActiveDocument.TransientDir
            )
            extension = _EXPORT_EXTENSIONS[filetype]
            basename = name + extension
            filename = os.path.join(export_directory, basename)

        # Relative/absolute path
        if self.relative_path and self.project_directory:
            res = os.path.relpath(filename, self.project_directory)
        else:
            res = filename

        # Escape characters
        res = res.encode("unicode_escape").decode("utf-8")

        # Skip meshing?
        if self.skip_meshing:
            return res

        # Switch to specialized write function
        if filetype == RenderMeshBase.ExportType.OBJ:
            mtlfile = kwargs.get("mtlfile")
            mtlname = kwargs.get("mtlname")
            mtlcontent = kwargs.get("mtlcontent")
            self._write_objfile(
                name,
                filename,
                mtlfile,
                mtlname,
                mtlcontent,
                uv_translate,
                uv_rotate,
                uv_scale,
            )
        elif filetype == RenderMeshBase.ExportType.PLY:
            self._write_plyfile(
                name, filename, uv_translate, uv_rotate, uv_scale
            )
        elif filetype == RenderMeshBase.ExportType.CYCLES:
            self._write_cyclesfile(name, filename)
        elif filetype == RenderMeshBase.ExportType.POVRAY:
            self._write_povfile(name, filename)
        else:
            raise ValueError(f"Unknown mesh file type '{filetype}'")

        # Return
        return res

    def _write_objfile(
        self,
        name,
        objfile=None,
        mtlfile=None,
        mtlname=None,
        mtlcontent=None,
        uv_translate=(0.0, 0.0),
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
            uv_translate -- UV translation vector (2-uple)
            uv_rotate -- UV rotation angle in degrees (float)
            uv_scale -- UV scale factor (float)

        Returns: the name of file that the function wrote.
        """
        tm0 = time.time()

        # Select routine (single or multi processing)
        if self.multiprocessing:
            func, mode = self._write_objfile_mp, "mp"
        else:
            func, mode = self._write_objfile_sp, "sp"

        # Mtl
        if mtlcontent is not None:
            # Material name
            mtlname = mtlname if mtlname else "material"
            # Target file
            if mtlfile is None:
                mtlfile, _ = os.path.splitext(objfile)
                mtlfile += ".mtl"
            # Write mtl file
            mtlfilename = RenderMeshBase._write_mtl(mtlname, mtlcontent, mtlfile)
            if os.path.dirname(mtlfilename) != os.path.dirname(objfile):
                raise ValueError(
                    "OBJ and MTL files shoud be in the same dir\n"
                    f"('{objfile}' versus '{mtlfilename}')"
                )
            mtlfilename = os.path.basename(mtlfilename)
        else:
            mtlfilename, mtlname = None, None

        # Pack uv transformation
        uv_transformation = (uv_translate, uv_rotate, uv_scale)

        # Call main routine (single or multi process)
        func(
            name,
            objfile,
            uv_transformation,
            mtlfilename,
            mtlname,
        )

        tm1 = time.time() - tm0
        debug("Object", self.name, f"Write OBJ file ({mode}): {tm1}")

    def _write_objfile_sp(
        self,
        name,
        objfile,
        uv_transformation,
        mtlfilename=None,
        mtlname=None,
    ):
        """Write an OBJ file from a mesh - single process.

        See write_objfile for more details.
        """
        # Header
        header = ["# Written by FreeCAD-Render\n"]

        # Mtl
        mtl = [f"mtllib {mtlfilename}\n\n"] if mtlfilename else []

        # Vertices
        fmtv = functools.partial(str.format, "v {} {} {}\n")
        verts = (fmtv(*v) for v in self.points)
        verts = it.chain(["# Vertices\n"], verts, ["\n"])

        # UV
        if self.has_uvmap():
            # Translate, rotate, scale (optionally)
            uvs = self.uvtransform(*uv_transformation)
            fmtuv = functools.partial(str.format, "vt {} {}\n")
            uvs = (fmtuv(*t) for t in uvs)
            uvs = it.chain(["# Texture coordinates\n"], uvs, ["\n"])
        else:
            uvs = []

        # Vertex normals
        if self.has_vnormals():
            norms = self.__vnormals
            fmtn = functools.partial(str.format, "vn {} {} {}\n")
            norms = (fmtn(*n) for n in norms)
            norms = it.chain(["# Vertex normals\n"], norms, ["\n"])
        else:
            norms = []

        # Object name
        objname = [f"o {name}\n"]
        if mtlname is not None:
            objname.append(f"usemtl {mtlname}\n")
        objname.append("\n")

        # Faces
        if self.has_vnormals() and self.has_uvmap():
            mask = " {0}/{0}/{0}"
        elif not self.has_vnormals() and self.has_uvmap():
            mask = " {0}/{0}"
        elif self.has_vnormals() and not self.has_uvmap():
            mask = " {0}//{0}"
        else:
            mask = " {}"

        fmtf = functools.partial(str.format, mask)
        joinf = functools.partial(str.join, "")

        faces = (
            joinf(["f"] + [fmtf(x + 1) for x in f] + ["\n"])
            for f in self.facets
        )
        faces = it.chain(["# Faces\n"], faces)

        res = it.chain(header, mtl, verts, uvs, norms, objname, faces)

        with open(objfile, "w", encoding="utf-8") as f:
            f.writelines(res)

    def _write_objfile_mp(
        self,
        name,
        objfile,
        uv_transformation,
        mtlfilename=None,
        mtlname=None,
    ):
        """Write an OBJ file from a mesh - multi process version.

        See write_objfile for more details.
        """
        # Initialize
        path = os.path.join(PKGDIR, "rendermesh_mp", "writeobj.py")

        # Header
        header = ["# Written by FreeCAD-Render\n"]

        # Mtl
        mtl = [f"mtllib {mtlfilename}\n\n"] if mtlfilename else []

        # UV
        if self.has_uvmap():
            # Translate, rotate, scale (optionally)
            uvs = self.uvtransform(*uv_transformation)
        else:
            uvs = []

        # Vertex normals
        if self.has_vnormals():
            norms = self.__vnormals
        else:
            norms = []

        # Object name
        objname = [f"o {name}\n"]
        if mtlname is not None:
            objname.append(f"usemtl {mtlname}\n")
        objname.append("\n")

        # Faces
        if self.has_vnormals() and self.has_uvmap():
            mask = " {0}/{0}/{0}"
        elif not self.has_vnormals() and self.has_uvmap():
            mask = " {0}/{0}"
        elif self.has_vnormals() and not self.has_uvmap():
            mask = " {0}//{0}"
        else:
            mask = " {}"

        inlist = [
            (header, "s"),
            (mtl, "s"),
            (self.points, "v"),
            (uvs, "vt"),
            (norms, "vn"),
            (objname, "s"),
            (self.facets, "f"),
        ]

        # Init script globals
        init_globals = {
            "inlist": inlist,
            "mask": mask,
            "objfile": objfile,
            "python": self.python,
        }

        # Run script
        self._run_path_in_process(path, init_globals)

    @staticmethod
    def _write_mtl(name, mtlcontent, mtlfile=None):
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

    def _write_plyfile(
        self,
        name,
        plyfile=None,
        uv_translate=(0.0, 0.0),
        uv_rotate=0.0,
        uv_scale=1.0,
    ):
        """Write an PLY file from a mesh.

        Args:
            name -- Name of the mesh (str)
            plyfile -- Name of the PLY file (str). If None, the PLY file is
              written in a temporary file, whose name is returned by the
              function.
            uv_translate -- UV translation vector (2-uple)
            uv_rotate -- UV rotation angle in degrees (float)
            uv_scale -- UV scale factor (float)

        Returns: the name of file that the function wrote.
        """
        # Header - Intro
        header = [
            "ply\n",
            "format ascii 1.0\n",
            "comment Created by FreeCAD-Render\n",
            f"comment '{name}'\n",
        ]

        # Header - Vertices (and vertex normals and uv)
        header += [
            f"element vertex {self.count_points}\n",
            "property float x\n",
            "property float y\n",
            "property float z\n",
        ]
        if self.has_vnormals():
            header += [
                "property float nx\n",
                "property float ny\n",
                "property float nz\n",
            ]
        if self.has_uvmap():
            header += [
                "property float s\n",
                "property float t\n",
            ]

        # Header - Faces
        header += [
            f"element face {self.count_facets}\n",
            "property list uchar int vertex_indices\n",
            "end_header\n",
        ]

        # Body - Vertices (and vertex normals and uv)
        fmt3 = functools.partial(str.format, "{} {} {}")
        verts = [iter(fmt3(*v) for v in self.points)]
        if self.has_vnormals():
            verts += [iter(fmt3(*v) for v in self.vnormals)]
        if self.has_uvmap():
            # Translate, rotate, scale (optionally)
            uvs = self.uvtransform(uv_translate, uv_rotate, uv_scale)
            fmt2 = functools.partial(str.format, "{} {}")
            verts += [iter(fmt2(*v) for v in uvs)]
        verts += [it.repeat("\n")]
        verts = (" ".join(v) for v in zip(*verts))

        # Body - Faces
        fmtf = functools.partial(str.format, "3 {} {} {}\n")
        faces = (fmtf(*v) for v in self.facets)

        # Concat and write
        res = it.chain(header, verts, faces)
        with open(plyfile, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(res)

    def _write_cyclesfile(
        self,
        name,
        cyclesfile=None,
    ):
        """Write a Cycles file from a mesh.

        Args:
            name -- Name of the mesh (str)
            cyclesfile -- Name of the Cycles file (str). If None, the Cycles
                file is written in a temporary file, whose name is returned by
                the function.
            uv_translate -- UV translation vector (2-uple)
            uv_rotate -- UV rotation angle in degrees (float)
            uv_scale -- UV scale factor (float)

        Returns: the name of file that the function wrote.
        """
        # TODO Stop rounding
        _rnd = functools.partial(
            round, ndigits=8
        )  # Round to 8 digits (helper)

        def _write_point(pnt):
            """Write a point."""
            return f"{_rnd(pnt[0])} {_rnd(pnt[1])} {_rnd(pnt[2])}"

        points = [_write_point(p) for p in self.points]
        points = "  ".join(points)
        verts = [f"{v[0]} {v[1]} {v[2]}" for v in self.facets]
        verts = "  ".join(verts)
        nverts = ["3"] * self.count_facets
        nverts = "  ".join(nverts)

        if self.has_uvmap():
            uvs = [f"{px} {py}" for px, py in self.uvmap_per_vertex()]
            uvs = "  ".join(uvs)
            uv_statement = f'    UV="{uvs}"\n'
        else:
            uv_statement = ""

        snippet_obj = f"""\
<?xml version="1.0" ?>
<!-- {name} -->
<cycles>
<mesh
    P="{points}"
    verts="{verts}"
    nverts="{nverts}"
{uv_statement}/>
</cycles>
"""

        # Write
        with open(cyclesfile, "w", encoding="utf-8") as f:
            f.write(snippet_obj)

    def _write_povfile(
        self,
        name,
        povfile=None,
    ):
        """Write an Povray file from a mesh.

        Args:
            name -- Name of the mesh (str)
            povfile -- Name of the Povray file (str). If None, the Povray file
                is written in a temporary file, whose name is returned by the
                function.
            uv_translate -- UV translation vector (2-uple)
            uv_rotate -- UV rotation angle in degrees (float)
            uv_scale -- UV scale factor (float)

        Returns: the name of file that the function wrote.
        """
        # Triangles
        vrts = [f"<{x},{y},{z}>" for x, y, z in self.points]
        inds = [f"<{i},{j},{k}>" for i, j, k in self.facets]

        vertices = "\n        ".join(vrts)
        len_vertices = len(vrts)
        indices = "\n        ".join(inds)
        len_indices = len(inds)

        # UV map
        if self.has_uvmap():
            uv_vectors = [f"<{tx},{ty}>" for tx, ty in self.uvmap]
            len_uv_vectors = len(uv_vectors)
            uv_vectors = "\n        ".join(uv_vectors)
            snippet_uv_vects = f"""\
        uv_vectors {{
            {len_uv_vectors},
            {uv_vectors}
        }}"""
        else:
            snippet_uv_vects = ""

        # Normals
        if self.has_vnormals():
            nrms = [f"<{nx},{ny},{nz}>" for nx, ny, nz in self.vnormals]
            normals = "\n        ".join(nrms)
            len_normals = len(nrms)
            snippet_normals = f"""\
        normal_vectors {{
            {len_normals},
            {normals}
        }}"""
        else:
            snippet_normals = ""

        snippet = f"""\
// Generated by FreeCAD-Render
// Declares object '{name}'
#declare {name} = mesh2 {{
    vertex_vectors {{
        {len_vertices},
        {vertices}
    }}
{snippet_normals}
{snippet_uv_vects}
    face_indices {{
        {len_indices},
        {indices}
    }}
}}  // {name}
"""

        # Write
        with open(povfile, "w", encoding="utf-8") as f:
            f.write(snippet)

    ##########################################################################
    #                               UV manipulations                         #
    ##########################################################################

    def uvtransform(self, translate, rotate, scale):
        """Compute a uv transformation (iterator).

        Args:
            uvmap -- the uv map to transform
            translate -- Translation vector (Vector2d)
            rotate -- Rotation angle in degrees (float)
            scale -- Scale factor (float)
        """
        uvmap = self.uvmap
        trans_x, trans_y = translate

        scale = float(scale)

        rotate = radians(float(rotate))

        def _000():
            """Nop."""
            return iter(uvmap)

        def _00t():
            """Translate."""
            return ((vec[0] + trans_x, vec[1] + trans_y) for vec in uvmap)

        def _0s0():
            """Scale."""
            return ((vec[0] * scale, vec[1] * scale) for vec in uvmap)

        def _0st():
            """Scale, translate."""
            return (
                (vec[0] * scale + trans_x, vec[1] * scale + trans_y)
                for vec in uvmap
            )

        def _r00():
            """Rotate."""
            cosr = cos(rotate)
            sinr = sin(rotate)
            return (
                (
                    vec[0] * cosr - vec[1] * sinr,
                    vec[0] * sinr + vec[1] * cosr,
                )
                for vec in uvmap
            )

        def _r0t():
            """Rotate, translate."""
            cosr = cos(rotate)
            sinr = sin(rotate)
            return (
                (
                    vec[0] * cosr - vec[1] * sinr + trans_x,
                    vec[0] * sinr + vec[1] * cosr + trans_y,
                )
                for vec in uvmap
            )

        def _rs0():
            """Rotate, scale."""
            cosrs = cos(rotate) * scale
            sinrs = sin(rotate) * scale
            return (
                (
                    vec[0] * cosrs - vec[1] * sinrs,
                    vec[0] * sinrs + vec[1] * cosrs,
                )
                for vec in uvmap
            )

        def _rst():
            """Rotate, scale, translate."""
            cosrs = cos(rotate) * scale
            sinrs = sin(rotate) * scale
            return (
                (
                    vec[0] * cosrs - vec[1] * sinrs + trans_x,
                    vec[0] * sinrs + vec[1] * cosrs + trans_y,
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

    @property
    def uvmap(self):
        """Get mesh uv map."""
        return self.__uvmap

    def uvmap_per_vertex(self):
        """Get mesh uv map by vertex.

        (used in Cycles)
        """
        return [
            self.__uvmap[vertex_index]
            for triangle in self.__facets
            for vertex_index in triangle
        ]

    def center_of_gravity(self):
        """Get mesh's center of gravity.

        Mesh CoG is the barycenter of the facets CoG, weighted by facets
        areas
        """

        def reducer(partial, facet):
            """Reduce facets for center of gravity computation."""
            sum1, sum2 = partial
            points, area = facet
            weight = area / len(points)
            facetbar = (sum(x) * weight for x in zip(*points))
            sum1 = tuple(x + y for x, y in zip(sum1, facetbar))
            sum2 += area
            return sum1, sum2

        facets = ((f.Points, f.Area) for f in self.__originalmesh.Facets)
        sum1, sum2 = functools.reduce(reducer, facets, ((0.0, 0.0, 0.0), 0.0))
        cog = App.Vector(sum1) / sum2
        return cog

    def compute_uvmap(self, projection):
        """Compute UV map for this mesh."""
        # Warning:
        # The computation should ensure consistency on the following data:
        # - self.__points
        # - self.__facets
        # - self.__normals
        # - self.__areas
        projection = "Cubic" if projection is None else projection
        tm0 = time.time()
        if projection == "Cubic":
            self._compute_uvmap_cube()
        elif projection == "Spherical":
            self._compute_uvmap_sphere()
        elif projection == "Cylindric":
            self._compute_uvmap_cylinder()
        else:
            raise ValueError
        debug("Object", self.name, f"Uvmap ending: {time.time() - tm0}")

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
            (atan2(p.x, p.y) * avg_radius * 0.001, p.z * 0.001) for p in points
        ]
        mesh.addMesh(regular_mesh)

        # Non Z-normal facets (seam)
        seam_mesh = Mesh.Mesh(seam)
        points = list(seam_mesh.Points)
        avg_radius = (
            sum(hypot(p.x, p.y) for p in points) / len(points) if points else 0
        )
        uvmap += [
            (_pos_atan2(p.x, p.y) * avg_radius * 0.001, p.z * 0.001)
            for p in points
        ]
        mesh.addMesh(seam_mesh)

        # Z-normal facets
        z_mesh = Mesh.Mesh(znormal)
        uvmap += [(p.x / 1000, p.y / 1000) for p in list(z_mesh.Points)]
        mesh.addMesh(z_mesh)

        # Replace previous values with newly computed ones
        points, facets = tuple(mesh.Topology)
        points = [tuple(p) for p in points]
        self.__points = points
        self.__facets = facets
        self.__normals = [tuple(f.Normal) for f in iter(mesh.Facets)]
        self.__areas = [f.Area for f in iter(mesh.Facets)]
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
            (
                (0.5 + atan2(v.x, v.y) / (2 * pi)) * (v.Length / 1000.0 * pi),
                (0.5 + asin(v.z / v.Length) / pi) * (v.Length / 1000.0 * pi),
            )
            for v in vectors
        ]
        mesh.addMesh(regular_mesh)

        # Seam facets
        seam_mesh = Mesh.Mesh(seam)
        vectors = [p.Vector - origin for p in list(seam_mesh.Points)]
        uvmap += [
            (
                (0.5 + _pos_atan2(v.x, v.y) / (2 * pi))
                * (v.Length / 1000.0 * pi),
                (0.5 + asin(v.z / v.Length) / pi) * (v.Length / 1000.0 * pi),
            )
            for v in vectors
        ]
        mesh.addMesh(seam_mesh)

        # Replace previous values with newly computed ones
        points, facets = tuple(mesh.Topology)
        self.__points = [tuple(p) for p in points]
        self.__facets = facets
        self.__normals = [tuple(f.Normal) for f in iter(mesh.Facets)]
        self.__areas = [f.Area for f in iter(mesh.Facets)]
        self.__uvmap = uvmap

    def _compute_uvmap_cube(self):
        """Compute UV map for cubic case.

        We isolate submeshes by cube face in order to avoid trouble when
        one edge belongs to several cube faces (cf. simple cube case, for
        instance)
        """
        if self.multiprocessing:
            msg = "Compute uvmap (mp)"
            func = self._compute_uvmap_cube_mp
        elif USE_NUMPY:
            msg = "Compute uvmap (np)"
            func = self._compute_uvmap_cube_np
        else:
            msg = "Compute uvmap (sp)"
            func = self._compute_uvmap_cube_sp

        debug("Object", self.name, msg)
        func()
        assert self.has_uvmap()

    def _compute_uvmap_cube_sp(self):
        """Compute UV map for cubic case - single process version.

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
        for cubeface, facets in enumerate(face_facets):
            facemesh = Mesh.Mesh(facets)
            # Compute uvmap of the submesh
            facemesh_uvmap = [
                _compute_uv_from_unitcube((p.Vector - cog) / 1000, cubeface)
                # pylint: disable=not-an-iterable
                for p in facemesh.Points
            ]
            # Add submesh and uvmap
            mesh.addMesh(facemesh)
            uvmap += facemesh_uvmap

        # Replace previous values with newly computed ones
        points, facets = tuple(mesh.Topology)
        points = [tuple(p) for p in points]
        self.__points = points
        self.__facets = facets
        self.__normals = [tuple(f.Normal) for f in iter(mesh.Facets)]
        self.__areas = [f.Area for f in iter(mesh.Facets)]
        self.__uvmap = uvmap

    def _compute_uvmap_cube_mp(self):
        """Compute UV map for cubic case - multiprocessing version.

        We isolate submeshes by cube face in order to avoid trouble when
        one edge belongs to several cube faces (cf. simple cube case, for
        instance)
        """
        # Init variables
        path = os.path.join(PKGDIR, "rendermesh_mp", "uvmap_cube.py")

        # Init output buffers
        facets = self.__facets
        facets_count = len(facets)
        color_count = 6
        points_per_facet = 3
        maxpoints = facets_count * color_count * points_per_facet

        points_buf = mp.RawArray("f", maxpoints * 3)
        facets_buf = mp.RawArray("l", len(facets) * 3)
        uvmap_buf = mp.RawArray("f", maxpoints * 2)
        point_count = mp.RawValue("l")

        # Init script globals
        init_globals = {
            "PYTHON": self.python,
            "POINTS": self.__points,
            "FACETS": self.__facets,
            "NORMALS": self.__normals,
            "AREAS": self.__areas,
            "SHOWTIME": PARAMS.GetBool("Debug"),
            "OUT_POINTS": points_buf,
            "OUT_FACETS": facets_buf,
            "OUT_UVMAP": uvmap_buf,
            "OUT_POINT_COUNT": point_count,
        }

        # Run script
        self._run_path_in_process(path, init_globals)

        # Get outputs
        point_count = point_count.value

        self.__points = list(grouper(points_buf[: point_count * 3], 3))
        self.__facets = list(grouper(facets_buf, 3))
        self.__uvmap = list(grouper(uvmap_buf[: point_count * 2], 2))

        points_buf = None
        facets_buf = None
        uvmap_buf = None

    def _compute_uvmap_cube_np(self):
        """Compute UV map for cubic case - numpy version."""
        debug_flag = PARAMS.GetBool("Debug")
        if debug_flag:
            time0 = time.time()

        # Set common parameters
        count_facets = self.count_facets
        normals = np.array(self.__normals)
        facets = np.array(self.facets)
        assert facets.shape[1] == 3
        points = np.array(self.points)
        areas = np.array(self.__areas)
        triangles = np.take(points, facets, axis=0)

        # Compute facet colors
        # Color is made of 2 terms:
        # First term: max of absolute coordinates of normals
        # Second term: sign of corresponding coordinate
        first_term = np.abs(normals)
        first_term = np.argmax(first_term, axis=1)  # Maximal coordinate
        first_term = np.expand_dims(first_term, axis=1)
        second_term = np.less(normals, np.zeros((count_facets, 3))).astype(int)
        second_term = np.take_along_axis(second_term, first_term, axis=1)
        facet_colors = first_term * 2 + second_term
        facet_colors = facet_colors.ravel()

        # Compute center of gravity (triangle cogs weighted by triangle areas)
        weighted_triangle_cogs = (
            np.add.reduce(triangles, 1) * areas[:, np.newaxis] / 3
        )
        cog = np.sum(weighted_triangle_cogs, axis=0) / np.sum(areas)

        # Update point list
        # Unfold facet points, joining with facet colors
        # Make them unique --> colored points
        tshape = triangles.shape
        unfolded_points = triangles.reshape(tshape[0] * tshape[1], tshape[2])
        unfolded_point_colors = np.expand_dims(facet_colors.repeat(3), axis=1)
        unfolded_colored_points = np.hstack(
            (unfolded_points, unfolded_point_colors)
        )
        colored_points, new_facets = np.unique(
            unfolded_colored_points, return_inverse=True, axis=0
        )

        # Save new points and facets
        new_facets = new_facets.reshape(count_facets, 3)
        new_points = colored_points[::, 0:3]

        # Compute uvmap
        # Center points to center of gravity.
        # Apply linear transformation to point coordinates.
        # The transformation depends on the point color.
        centered_points = new_points - cog
        point_colors = colored_points[::, 3].astype(np.int64)
        base_matrices = np.array(
            [
                [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                [[0.0, -1.0, 0.0], [0.0, 0.0, 1.0]],
                [[-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
                [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
                [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0]],
            ]
        )
        uvs = np.matmul(
            base_matrices.take(point_colors, axis=0),
            np.expand_dims(centered_points, axis=2),
            axes=[(1, 2), (1, 2), (1, 2)],
        )
        uvs = uvs.squeeze(axis=2)
        uvs /= 1000  # Scale

        # Update attributes
        self.__facets = new_facets.tolist()
        self.__points = new_points.tolist()
        self.__uvmap = uvs.tolist()

        if debug_flag:
            print("numpy", time.time() - time0)

    ##########################################################################
    #                       Vertex Normals manipulations                     #
    ##########################################################################

    def compute_vnormals(self):
        """Compute vertex normals - entry point."""
        if self.multiprocessing:
            msg = "Compute vertex normals (mp)"
            func = self._compute_vnormals_mp
        elif USE_NUMPY:
            msg = "Compute vertex normals (np)"
            func = self._compute_vnormals_np
        else:
            msg = "Compute vertex normals (sp)"
            func = self._compute_vnormals_sp

        debug("Object", self.name, msg)
        func()

    def _compute_vnormals_np(self):
        """Compute vertex normals (numpy version).

        Refresh self._normals. We use an area & angle weighting algorithm."
        """
        debug_flag = PARAMS.GetBool("Debug")
        if debug_flag:
            print("compute vnormals Numpy")
            tm0 = time.time()

        # Prepare parameters
        points = np.array(self.__points, dtype="f4")
        normals = np.array(self.__normals, dtype="f4")
        areas = np.array(self.__areas, dtype="f4")
        facets = np.array(self.__facets, dtype="i4")
        triangles = np.take(points, facets, axis=0)
        indices = facets.ravel(order="F")

        if debug_flag:
            print("init", time.time() - tm0)

        def _safe_normalize_np(vect_array):
            """Safely normalize an array of vectors."""
            magnitudes = np.sqrt((vect_array**2).sum(-1))
            magnitudes = np.expand_dims(magnitudes, axis=1)
            return np.divide(vect_array, magnitudes, where=magnitudes != 0.0)

        def _angles(i, j, k):
            """Compute triangle vertex angles."""
            # Compute normalized vectors
            vec1 = triangles[::, j, ::] - triangles[::, i, ::]
            vec1 = _safe_normalize_np(vec1)

            vec2 = triangles[::, k, ::] - triangles[::, i, ::]
            vec2 = _safe_normalize_np(vec2)

            # Compute dot products
            # (Clip to avoid precision issues)
            dots = (vec1 * vec2).sum(axis=1).clip(-1.0, 1.0)

            # Compute arccos of dot products
            angles = np.arccos(dots)
            return angles

        # Reminder:
        # local a1 = AngleBetweenVectors (v1-v0) (v2-v0)
        # local a2 = AngleBetweenVectors (v0-v1) (v2-v1)
        # local a3 = AngleBetweenVectors (v0-v2) (v1-v2)
        angles0 = _angles(0, 1, 2)
        angles1 = _angles(1, 0, 2)
        angles2 = np.pi - angles1 - angles0
        # Debug
        # assert np.all(np.isclose(angles0+angles1+_angles(2, 0, 1),np.pi))
        vertex_angles = np.concatenate((angles0, angles1, angles2))
        if debug_flag:
            print("angles", time.time() - tm0)

        # Compute weighted normals for each vertex of the triangles
        vertex_areas = np.concatenate((areas, areas, areas))
        weights = vertex_areas * vertex_angles
        weights = np.expand_dims(weights, axis=1)

        vertex_normals = np.concatenate((normals, normals, normals), axis=0)
        weighted_normals = vertex_normals * weights

        if debug_flag:
            print("vertex weighted normals", time.time() - tm0)

        # Weighted sum of normals
        point_normals = np.column_stack(
            (
                np.bincount(indices, weighted_normals[..., 0]),
                np.bincount(indices, weighted_normals[..., 1]),
                np.bincount(indices, weighted_normals[..., 2]),
            )
        )
        point_normals = _safe_normalize_np(point_normals)

        self.__vnormals = point_normals.tolist()

        if debug_flag:
            print(time.time() - tm0)

    def _compute_vnormals_sp(self):
        """Compute vertex normals (single process).

        Refresh self._normals. We use an area & angle weighting algorithm."
        """
        # See here
        # http://www.bytehazard.com/articles/wnormals.html
        # (and look at script wnormals100.ms)

        fmul = vector3d.fmul
        v3d_angles = vector3d.angles
        add = vector3d.add
        safe_normalize = vector3d.safe_normalize
        points = self.__points
        normals = self.__normals
        areas = self.__areas
        facets = self.__facets

        vnorms = [(0, 0, 0)] * self.count_points

        it_facets = (
            (facet, normal, area, v3d_angles(points[i] for i in facet))
            for facet, normal, area in zip(facets, normals, areas)
        )
        it_points = (
            (point_index, fmul(normal, angle * area))
            for facet, normal, area, angles in it_facets
            for point_index, angle in zip(facet, angles)
        )

        def vnorm_reducer(rolling, new):
            point_index, weighted_vnorm = new
            rolling[point_index] = add(rolling[point_index], weighted_vnorm)
            return rolling

        vnorms = functools.reduce(vnorm_reducer, it_points, vnorms)

        # Normalize
        vnorms = [safe_normalize(n) for n in vnorms]

        self.__vnormals = vnorms

    def _compute_vnormals_mp(self):
        """Compute vertex normals (single process).

        Refresh self._normals. We use an area & angle weighting algorithm."
        """
        # Init variables
        path = os.path.join(PKGDIR, "rendermesh_mp", "compute_vnormals.py")

        # Init output buffer
        vnormals_buf = mp.RawArray("f", self.count_points * 3)

        # Init script globals
        init_globals = {
            "POINTS": mp.RawArray("f", SharedWrapper(self.__points, 3)),
            "FACETS": mp.RawArray("l", SharedWrapper(self.__facets, 3)),
            "NORMALS": mp.RawArray("f", SharedWrapper(self.__normals, 3)),
            "AREAS": mp.RawArray("f", self.__areas),
            "PYTHON": self.python,
            "SHOWTIME": PARAMS.GetBool("Debug"),
            "OUT_VNORMALS": vnormals_buf,
        }

        # Run script
        self._run_path_in_process(path, init_globals)

        # Update properties
        vnormals_mv = (
            memoryview(vnormals_buf)
            .cast("b")
            .cast("f", [self.count_points, 3])
        )
        self.__vnormals = vnormals_mv.tolist()

    def _adjacent_facets(self):
        """Compute the adjacent facets for each facet of the mesh.

        Returns a list of sets of facet indices (adjacency list).
        Entry point.
        """
        if USE_NUMPY:
            msg = "compute adjacency lists (np)"
            func = self._adjacent_facets_np
        else:
            msg = "compute adjacency lists (sp)"
            func = self._adjacent_facets_sp

        debug_flag = PARAMS.GetBool("Debug")
        if debug_flag:
            print("\n" + msg + f" - {self.count_facets} facets")

        return func()

    def _adjacent_facets_sp(self):
        """Compute the adjacent facets for each facet of the mesh.

        Returns a list of sets of facet indices (adjacency list).
        Single process version.
        """
        debug_flag = PARAMS.GetBool("Debug")
        if debug_flag:
            tm0 = time.time()

        # For each point, compute facets that contain this point as a vertex
        iterator = (
            (facet_index, point_index)
            for facet_index, facet in enumerate(self.__facets)
            for point_index in facet
        )

        def fpp_reducer(_, new):
            facet_index, point_index = new
            facets_per_point[point_index].append(facet_index)

        facets_per_point = [[] for _ in range(self.count_points)]
        functools.reduce(fpp_reducer, iterator, None)

        # Compute adjacency
        facets = [set(f) for f in self.__facets]
        iterator = (
            (facet_idx, other_idx)
            for facet_idx, facet in enumerate(facets)
            for point_idx in facet
            for other_idx in facets_per_point[point_idx]
            if len(facet & facets[other_idx]) == 2
        )

        adjacents = [set() for _ in range(self.count_facets)]

        def reduce_adj(_, new):
            facet_index, other_index = new
            adjacents[facet_index].add(other_index)

        functools.reduce(reduce_adj, iterator, None)

        if debug_flag:
            print("adjacency", time.time() - tm0)

        return adjacents

    def _adjacent_facets_np(self):
        """Compute the adjacent facets for each facet of the mesh.

        Returns a list of sets of facet indices (adjacency list).
        Numpy version
        """
        debug_flag = PARAMS.GetBool("Debug")
        if debug_flag:
            print()
            print(f"compute adjacency Numpy - {self.count_facets} facets")
            tm0 = time.time()
            np.set_printoptions(edgeitems=600)

        # Compute edges (assume triangles)
        facets = np.asarray(self.__facets)
        facets.sort(axis=1)

        indices = np.arange(len(facets))
        indices = np.tile(indices, 3)

        edges1 = np.rec.fromarrays((facets[..., 0], facets[..., 1]))
        edges2 = np.rec.fromarrays((facets[..., 0], facets[..., 2]))
        edges3 = np.rec.fromarrays((facets[..., 1], facets[..., 2]))
        edges = np.concatenate((edges1, edges2, edges3))

        if debug_flag:
            print("edges", time.time() - tm0)

        argsort_edges = edges.argsort()
        sorted_facet_indices = indices[argsort_edges]
        sorted_edges = edges[argsort_edges]

        if debug_flag:
            print("edges sorted", time.time() - tm0)

        # Searches
        unique_edges, unique_indices, unique_counts = np.unique(
            sorted_edges, return_index=True, return_counts=True
        )
        unique_indices_left = np.searchsorted(unique_edges, edges, side="left")
        indices_left = unique_indices[unique_indices_left]
        indices_count = unique_counts[unique_indices_left]
        indices_right = indices_left + indices_count - 1
        maxindices = np.max(indices_count)
        if maxindices > 2:  # We assume only 2 neighbours per edge
            msg = (
                "Warning - More than 2 neighbours per edge "
                f"(found {maxindices})"
                " - Truncation may occur"
            )
            warn("Object", self.name, msg)
        indices_left = sorted_facet_indices[indices_left]
        indices_right = sorted_facet_indices[indices_right]

        pairs_left = np.rec.fromarrays((indices, indices_left), names="x,y")
        condition_left = np.not_equal(pairs_left.x, pairs_left.y)
        pairs_left = np.compress(condition_left, pairs_left)

        pairs_right = np.rec.fromarrays((indices, indices_right), names="x,y")
        condition_right = np.not_equal(pairs_right.x, pairs_right.y)
        pairs_right = np.compress(condition_right, pairs_right)

        if debug_flag:
            print("searches", time.time() - tm0)

        # Concatenate
        pairs = np.concatenate((pairs_left, pairs_right))
        adjacency = [set() for _ in range(self.count_facets)]
        for index, value in pairs:
            adjacency[index].add(value)

        if debug_flag:
            print("adjacency", time.time() - tm0)

        return adjacency

    def connected_facets(
        self,
        starting_facet_index,
        adjacents,
        tags,
        new_tag,
        split_angle_cos,
    ):
        """Get the maximal connected component containing the starting facet.

        It uses a depth-first search algorithm, iterative version.
        Caveat:
        - tags may be modified by the algorithm.

        Args:
            starting_facet_index -- the index of the facet to start
                with (integer)
            adjacents -- adjacency lists (one list per facet)
            tags -- the tags that have already been set (list, same size as
                self.__facets)
            new_tag -- the tag to use to mark the component
            split_angle_cos -- the cos of the angle that breaks adjacency

        Returns:
            A list of tags (same size as self.__facets). The elements tagged
            with 'new_tag' are the computed connected component.
        """
        # Init
        split_angle_cos = float(split_angle_cos)
        dot = vector3d.dot
        normals = self.__normals

        # Create and init stack
        stack = [starting_facet_index]

        # Tag starting facet
        tags[starting_facet_index] = new_tag

        while stack:
            # Current index (stack top)
            current_index = stack[-1]
            current_normal = normals[current_index]

            # Forward
            while adjacents[current_index]:
                successor_index = adjacents[current_index].pop()

                # Test angle
                try:
                    successor_normal = normals[successor_index]
                except IndexError:
                    # Facet.NeighbourIndices can contain irrelevant index...
                    continue

                if dot(current_normal, successor_normal) < split_angle_cos:
                    continue

                if tags[successor_index] is None:
                    # successor is not tagged, we can go on forward
                    tags[successor_index] = new_tag
                    stack.append(successor_index)
                    current_index = successor_index
                    current_normal = normals[current_index]

            # Backward
            successor_index = stack.pop()

        # Final
        return tags

    def _connected_components_sp(self, split_angle=radians(30)):
        """Get all connected components of facets in the mesh.

        Single process version

        Args:
            split_angle -- the angle that breaks adjacency

        Returns:
            a list of tags. Each tag gives the component of the corresponding
                facet
            the number of components
        """
        split_angle_cos = cos(split_angle)

        adjacents = self._adjacent_facets()

        tags = [None] * self.count_facets
        tag = None

        iterator = zip(
            it.count(), (x for x, y in enumerate(tags) if y is None)
        )
        for tag, starting_point in iterator:
            tags = self.connected_facets(
                starting_point, adjacents, tags, tag, split_angle_cos
            )

        return tags

    def _connected_components_mp(self, split_angle):
        """Get all connected components of facets in the mesh.

        Multiprocess version

        Args:
            split_angle -- the angle that breaks adjacency (radians)

        Returns:
            a list of tags. Each tag gives the component of the corresponding
                facet
            the number of components
        """
        # Init variables
        path = os.path.join(PKGDIR, "rendermesh_mp", "connected_components.py")

        # Init output buffer
        tags_buf = mp.RawArray("l", self.count_facets)

        # Init script globals
        init_globals = {
            "POINTS": mp.RawArray("f", SharedWrapper(self.__points, 3)),
            "FACETS": mp.RawArray("l", SharedWrapper(self.__facets, 3)),
            "NORMALS": mp.RawArray("f", SharedWrapper(self.__normals, 3)),
            "AREAS": mp.RawArray("f", self.__areas),
            "SPLIT_ANGLE": mp.RawValue("f", split_angle),
            "PYTHON": self.python,
            "SHOWTIME": PARAMS.GetBool("Debug"),
            "OUT_TAGS": tags_buf,
        }

        # Run script
        self._run_path_in_process(path, init_globals)

        # Update properties
        tags = list(tags_buf[::])

        return tags

    def connected_components(self, split_angle):
        """Get all connected components of facets in the mesh.

        Single process version

        Args:
            split_angle -- the angle that breaks adjacency (radians)

        Returns:
            a list of tags. Each tag gives the component of the corresponding
                facet
            the number of components
        """
        if self.multiprocessing:
            msg = "Compute connected components (mp)"
            func = self._connected_components_mp
        elif USE_NUMPY:
            msg = "Compute connected components (sp)"
            func = self._connected_components_sp
        else:
            msg = "Compute connected components (sp)"
            func = self._connected_components_sp

        debug("Object", self.name, msg)
        return func(split_angle)

    def separate_connected_components(self, split_angle=radians(30)):
        """Operate a separation into the mesh between connected components.

        Only points are modified. Facets are kept as-is.

        Args:
            split_angle -- angle threshold, above which 2 adjacents facets
                are considered as non-connected (in radians)
        """
        tags = self.connected_components(split_angle)

        points = self.__points
        facets = self.__facets

        # Initialize the map
        newpoints = {
            (point_index, tag): None
            for facet, tag in zip(facets, tags)
            for point_index in facet
        }

        # Number newpoint
        for index, point in enumerate(newpoints):
            newpoints[point] = index

        # Rebuild point list
        self.__points = [points[point_index] for point_index, tag in newpoints]

        # If necessary, rebuild uvmap
        if self.__uvmap:
            self.__uvmap = [
                self.__uvmap[point_index] for point_index, tag in newpoints
            ]

        # Update point indices in facets
        self.__facets = [
            tuple(newpoints[point_index, tag] for point_index in facet)
            for facet, tag in zip(facets, tags)
        ]

    def _run_path_in_process(self, path, init_globals):
        """Run a path in a dedicated process.

        This method is able to launch a multiprocess script, like
        runpy.run_path. However it solves the lack of thread safety of
        'runpy.run_path', by embedding run_path in a dedicated process.
        Please note 'self.python' must have been set. After
        being started, the process is awaited (joined).
        """
        args = (path,)
        kwargs = {"init_globals": init_globals, "run_name": "__main__"}

        mp.set_executable(self.python)

        process = mp.Process(
            target=runpy.run_path, args=args, kwargs=kwargs, name="render"
        )
        process.start()
        process.join()


# ===========================================================================
#                               RenderTransformation
# ===========================================================================


class _Transformation:
    """A extension of Placement, implementing also scale."""

    def __init__(self, placement=App.Placement(), scale=1.0):
        """Initialize transformation."""
        self.__placement = App.Placement(placement)
        self.__scale = float(scale)

    def apply_placement(self, placement, left=False):
        """Apply a FreeCAD placement to this.

        By default, placement is applied on the right, but it can also be
        applied on the left, with 'left' parameter.

        """
        placement = App.Placement(placement)
        if not left:
            self.__placement *= placement
        else:
            placement *= self.__placement
            self.__placement = placement

    def __str__(self):
        """Give a string representation."""
        return f"Placement={self.__placement}, Scale={self.__scale}"

    @property
    def scale(self):
        """Get scale property."""
        return self.__scale

    @scale.setter
    def scale(self, new_scale):
        """Set scale property."""
        new_scale = float(new_scale)
        assert new_scale, "new_scale cannot be zero"
        self.__scale = new_scale

    # Getters
    def get_matrix_fcd(self):
        """Get transformation matrix in FreeCAD format."""
        mat = App.Matrix(self.__placement.toMatrix())

        # Scale
        scale = self.__scale
        mat.scale(self.__scale)
        mat.A41 *= scale
        mat.A42 *= scale
        mat.A43 *= scale

        return mat

    def get_matrix_rows(self):
        """Get transformation matrix as a list of rows."""
        mat = self.__placement.Matrix

        # Get plain transfo
        transfo_rows = [mat.A[i * 4 : (i + 1) * 4] for i in range(4)]

        # Apply scale
        transfo_rows = [
            [val * self.__scale if rownumber < 3 else val for val in row]
            for rownumber, row in enumerate(transfo_rows)
        ]
        return transfo_rows

    def get_matrix_columns(self):
        """Get transformation matrix as a list of columns."""
        transfo_rows = self.get_matrix_rows()
        transfo_cols = list(zip(*transfo_rows))
        return transfo_cols

    def get_translation(self):
        """Get translation component."""
        scale = self.__scale
        return tuple(v * scale for v in tuple(self.__placement.Base))

    def get_rotation_qtn(self):
        """Get rotation component as a quaternion."""
        return tuple(self.__placement.Rotation.Q)

    def get_rotation_ypr(self):
        """Get rotation component as yaw-pitch-roll angles."""
        try:
            # >0.20
            return self.__placement.Rotation.getYawPitchRoll()
        except AttributeError:
            # 0.19
            return self.__placement.Rotation.toEuler()

    def get_scale(self):
        """Get scale component as single scalar."""
        return self.__scale

    def get_scale_vector(self):
        """Get scale component as vector."""
        scale = self.__scale
        return (scale, scale, scale)


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


def _uc_xplus(point):
    """Unit cube - xplus case."""
    _, pt1, pt2 = point
    return (pt1, pt2)


def _uc_xminus(point):
    """Unit cube - xminus case."""
    _, pt1, pt2 = point
    return (-pt1, pt2)


def _uc_yplus(point):
    """Unit cube - yplus case."""
    pt0, _, pt2 = point
    return (-pt0, pt2)


def _uc_yminus(point):
    """Unit cube - yminus case."""
    pt0, _, pt2 = point
    return (pt0, pt2)


def _uc_zplus(point):
    """Unit cube - zplus case."""
    pt0, pt1, _ = point
    return (pt0, pt1)


def _uc_zminus(point):
    """Unit cube - zminus case."""
    pt0, pt1, _ = point
    return (pt0, -pt1)


_UC_MAP = (
    _uc_xplus,
    _uc_xminus,
    _uc_yplus,
    _uc_yminus,
    _uc_zplus,
    _uc_zminus,
)


def _compute_uv_from_unitcube(point, face):
    """Compute UV coords from intersection point and face.

    The cube is unfold this way:

          +Z
    +X +Y -X -Y
          -Z

    """
    # pt0, pt1, pt2 = point
    # if face == 0:  # _UnitCubeFaceEnum.XPLUS
    # res = (pt1, pt2)
    # elif face == 1:  # _UnitCubeFaceEnum.XMINUS
    # res = (-pt1, pt2)
    # elif face == 2:  # _UnitCubeFaceEnum.YPLUS
    # res = (-pt0, pt2)
    # elif face == 3:  # _UnitCubeFaceEnum.YMINUS
    # res = (pt0, pt2)
    # elif face == 4:  # _UnitCubeFaceEnum.ZPLUS
    # res = (pt0, pt1)
    # elif face == 5:  # _UnitCubeFaceEnum.ZMINUS
    # res = (pt0, -pt1)
    method = _UC_MAP[face]
    return method(point)


# ===========================================================================
#                           Other uvmap helpers
# ===========================================================================


def _safe_normalize(vec):
    """Safely normalize a FreeCAD Vector.

    If vector's length is 0, returns (0, 0, 0).
    """
    try:
        res = vec.normalize()
    except App.Base.FreeCADError:
        res = App.Base.Vector(0.0, 0.0, 0.0)
    return res


def _is_facet_normal_to_vector(facet, vector):
    """Test whether a facet is normal to a vector.

    math.isclose is used to assess dot product nullity.
    """
    pt1, pt2, pt3 = facet.Points
    vec1 = _safe_normalize(App.Base.Vector(*pt2) - App.Base.Vector(*pt1))
    vec2 = _safe_normalize(App.Base.Vector(*pt3) - App.Base.Vector(*pt1))
    vector = _safe_normalize(vector)
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


# ===========================================================================
#                           Miscellaneous
# ===========================================================================


_EXPORT_EXTENSIONS = {
    RenderMeshBase.ExportType.OBJ: ".obj",
    RenderMeshBase.ExportType.PLY: ".ply",
    RenderMeshBase.ExportType.CYCLES: ".xml",
    RenderMeshBase.ExportType.POVRAY: ".inc",
}


def _find_python():
    """Find Python executable."""
    python = shutil.which("pythonw")
    if python:
        python = os.path.abspath(python)
        return python

    python = shutil.which("python")
    if python:
        python = os.path.abspath(python)
        return python

    return None


def _check_directory(directory):
    """Check if directory is consistent (or None)."""
    if directory is None:
        return directory
    if not os.path.isdir(directory):
        msg = f"Mesh: invalid directory '{directory}'"
        raise ValueError(msg)
    return directory
