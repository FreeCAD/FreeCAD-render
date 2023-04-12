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

"""RenderMesh mixins, to add various capabilities to RenderMesh base.

Capabilities are added by overloading base class methods.
"""

import runpy
import multiprocessing as mp
import shutil
import os
import time

try:
    import numpy as np
except ModuleNotFoundError:
    pass

from Render.constants import PKGDIR, PARAMS
from Render.utils import warn, debug, grouper, SharedWrapper

try:
    mp.set_start_method("spawn")
except RuntimeError:
    # Already set...
    pass

# ===========================================================================
#                           Multiprocess mixin
# ===========================================================================


class RenderMeshMultiprocessingMixin:
    """A mixin class to add multiprocessing capabilities to RenderMesh."""

    def __init__(self, *args, **kwargs):
        """Initialize mixin."""
        self.python = _find_python()
        super().__init__(*args, **kwargs)

    def _compute_uvmap_cube(self):
        """Compute UV map for cubic case - multiprocessing version.

        We isolate submeshes by cube face in order to avoid trouble when
        one edge belongs to several cube faces (cf. simple cube case, for
        instance)
        """
        debug("Object", self.name, "Compute uvmap (mp)")

        # Init variables
        path = os.path.join(PKGDIR, "rendermesh_mp", "uvmap_cube.py")

        # Init output buffers
        facets = self.facets
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
            "POINTS": self.points,
            "FACETS": self.facets,
            "NORMALS": self.normals,
            "AREAS": self.areas,
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

        self.points = list(grouper(points_buf[: point_count * 3], 3))
        self.facets = list(grouper(facets_buf, 3))
        self.uvmap = list(grouper(uvmap_buf[: point_count * 2], 2))

        points_buf = None
        facets_buf = None
        uvmap_buf = None

    def compute_vnormals(self):
        """Compute vertex normals (single process).

        Refresh self._normals. We use an area & angle weighting algorithm."
        """
        debug("Object", self.name, "Compute vertex normals (mp)")

        # Init variables
        path = os.path.join(PKGDIR, "rendermesh_mp", "compute_vnormals.py")

        # Init output buffer
        vnormals_buf = mp.RawArray("f", self.count_points * 3)

        # Init script globals
        init_globals = {
            "POINTS": mp.RawArray("f", SharedWrapper(self.points, 3)),
            "FACETS": mp.RawArray("l", SharedWrapper(self.facets, 3)),
            "NORMALS": mp.RawArray("f", SharedWrapper(self.normals, 3)),
            "AREAS": mp.RawArray("f", self.areas),
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

    def connected_components(self, split_angle):
        """Get all connected components of facets in the mesh.

        Multiprocess version

        Args:
            split_angle -- the angle that breaks adjacency (radians)

        Returns:
            a list of tags. Each tag gives the component of the corresponding
                facet
            the number of components
        """
        debug("Object", self.name, "Compute connected components (mp)")

        # Init variables
        path = os.path.join(PKGDIR, "rendermesh_mp", "connected_components.py")

        # Init output buffer
        tags_buf = mp.RawArray("l", self.count_facets)

        # Init script globals
        init_globals = {
            "POINTS": mp.RawArray("f", SharedWrapper(self.points, 3)),
            "FACETS": mp.RawArray("l", SharedWrapper(self.facets, 3)),
            "NORMALS": mp.RawArray("f", SharedWrapper(self.normals, 3)),
            "AREAS": mp.RawArray("f", self.areas),
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

    def _write_objfile_helper(
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
#                           Numpy mixin
# ===========================================================================


class RenderMeshNumpyMixin:
    """A mixin class to add Numpy use capabilities to RenderMesh."""

    def _compute_uvmap_cube(self):
        """Compute UV map for cubic case - numpy version."""

        debug("Object", self.name, "Compute uvmap (np)")

        debug_flag = PARAMS.GetBool("Debug")
        if debug_flag:
            time0 = time.time()

        # Set common parameters
        count_facets = self.count_facets
        normals = np.array(self.normals)
        facets = np.array(self.facets)
        assert facets.shape[1] == 3
        points = np.array(self.points)
        areas = np.array(self.areas)
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
        self.facets = new_facets.tolist()
        self.points = new_points.tolist()
        self.uvmap = uvs.tolist()

        if debug_flag:
            print("numpy", time.time() - time0)

    def compute_vnormals(self):
        """Compute vertex normals (numpy version).

        Refresh self._normals. We use an area & angle weighting algorithm."
        """
        debug("Object", self.name, "Compute vertex normals (np)")

        debug_flag = PARAMS.GetBool("Debug")
        if debug_flag:
            print("compute vnormals Numpy")
            tm0 = time.time()

        # Prepare parameters
        points = np.array(self.points, dtype="f4")
        normals = np.array(self.normals, dtype="f4")
        areas = np.array(self.areas, dtype="f4")
        facets = np.array(self.facets, dtype="i4")
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

        self.vnormals = point_normals.tolist()

        if debug_flag:
            print(time.time() - tm0)

    def _adjacent_facets(self):
        """Compute the adjacent facets for each facet of the mesh.

        Returns a list of sets of facet indices (adjacency list).
        Numpy version
        """
        debug_flag = PARAMS.GetBool("Debug")
        if debug_flag:
            print()
            print(f"compute adjacency lists (np) - {self.count_facets} facets")
            tm0 = time.time()
            np.set_printoptions(edgeitems=600)

        # Compute edges (assume triangles)
        facets = np.asarray(self.facets)
        facets.sort(axis=1)

        indices = np.arange(len(facets))
        indices = np.tile(indices, 3)

        edges = np.concatenate(
            (
                np.rec.fromarrays((facets[..., 0], facets[..., 1])),
                np.rec.fromarrays((facets[..., 0], facets[..., 2])),
                np.rec.fromarrays((facets[..., 1], facets[..., 2])),
            )
        )

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


# ===========================================================================
#                               Helpers
# ===========================================================================


def multiprocessing_enabled(mesh):
    """Check if multiprocessing can be enabled."""
    conditions = (
        PARAMS.GetBool("EnableMultiprocessing"),
        mesh.CountPoints >= 2000,
        _find_python(),
    )
    return all(conditions)


def numpy_enabled():
    """Check if multiprocessing can be enabled."""
    conditions = (
        "np" in globals(),
        PARAMS.GetBool("EnableNumpy"),
    )
    return all(conditions)


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
