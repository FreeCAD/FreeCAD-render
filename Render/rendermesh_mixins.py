# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2023 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
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
from multiprocessing import connection, shared_memory
import shutil
import os
import time
import itertools
import operator
import functools
from math import radians, cos
import copy

try:
    import numpy as np
except ModuleNotFoundError:
    pass


from Render.constants import PKGDIR, PARAMS
from Render.utils import warn, debug, grouper

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

    def _setup_internals(self):
        """Set up internal variables.

        To be overidden by mixins if necessary.
        """
        mesh = self._originalmesh
        points, facets = mesh.Topology
        facets2 = mesh.Facets
        count_points = mesh.CountPoints
        count_facets = mesh.CountFacets

        if PARAMS.GetBool("Debug"):
            print(f"{count_points} points, {count_facets} facets")

        self._points = SharedArray("f", count_points, 3, points)
        self._facets = SharedArray("l", count_facets, 3, facets)
        self._normals = SharedArray(
            "f", count_facets, 3, [f.Normal for f in facets2]
        )
        self._areas = mp.RawArray("f", count_facets)
        self._areas[:] = [f.Area for f in facets2]

        self._uvmap = SharedArray("f", 0, 2)

        self._vnormals = SharedArray("f", 0, 3)

    @property
    def points(self):
        """Get points."""
        return self._points

    @points.setter
    def points(self, value):
        """Set points."""
        self._points = SharedArray("f", len(value), 3, value)

    @property
    def count_points(self):
        """Get number of points."""
        return len(self._points)

    @property
    def facets(self):
        """Get facets."""
        return self._facets

    @facets.setter
    def facets(self, value):
        """Set facets."""
        self._facets = SharedArray("l", len(value), 3, value)

    @property
    def count_facets(self):
        """Get number of facets."""
        return len(self._facets)

    @property
    def normals(self):
        """Get facet normals."""
        return self._normals

    @normals.setter
    def normals(self, value):
        """Set facet normals."""
        self._normals = SharedArray("f", len(value), 3, value)

    @property
    def areas(self):
        """Get facet areas."""
        return self._areas

    @areas.setter
    def areas(self, value):
        """Set facet areas."""
        self._areas = mp.RawArray("f", len(value))
        self._areas[:] = value

    @property
    def uvmap(self):
        """Get uv map."""
        return (complex(r, i) for r, i in self._uvmap)

    @uvmap.setter
    def uvmap(self, value):
        """Set uv map."""
        self._uvmap = SharedArray("f", len(value), 2, value)

    @property
    def vnormals(self):
        """Get vertex normals."""
        return self._vnormals

    @vnormals.setter
    def vnormals(self, value):
        """Set vertex normals."""
        self._vnormals = SharedArray("f", len(value), 3, value)

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
        color_count = 6
        points_per_facet = 3
        maxpoints = self.count_facets * color_count * points_per_facet

        points_buf = mp.RawArray("f", maxpoints * 3)
        facets_buf = mp.RawArray("l", self.count_facets * 3)
        uvmap_buf = mp.RawArray("f", maxpoints * 2)
        point_count = mp.RawValue("l")

        # Init script globals
        init_globals = {
            "PYTHON": self.python,
            "POINTS": self._points.array,
            "FACETS": self._facets.array,
            "NORMALS": self._normals.array,
            "AREAS": self._areas,
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

        self._points.array = points_buf[: point_count * 3]
        self._facets.array = facets_buf
        self.uvmap = list(grouper(uvmap_buf[: point_count * 2], 2))

        points_buf = None
        facets_buf = None
        uvmap_buf = None

    def autosmooth(self, split_angle):
        """Smooth mesh, computing vertex normals.

        Multiprocess version

        Args:
            split_angle -- the angle that breaks adjacency (radians)
        """
        debug("Object", self.name, "Compute connected components (mp)")

        tm0 = time.time()

        # Init variables
        path = os.path.join(PKGDIR, "rendermesh_mp", "autosmooth.py")

        if debug_flag := PARAMS.GetBool("Debug"):
            print(f"Connected components: {self.count_points} points")

        # Init script globals
        init_globals = {
            "POINTS": self._points.array,
            "FACETS": self._facets.array,
            "NORMALS": self._normals.array,
            "AREAS": self._areas,
            "UVMAP": self._uvmap.array,
            "SPLIT_ANGLE": mp.RawValue("f", split_angle),
            "PYTHON": self.python,
            "SHOWTIME": PARAMS.GetBool("Debug"),
        }

        if debug_flag:
            print("init connected", time.time() - tm0)

        # Run script (return points, facets, vnormals, uvmap)
        result = self._run_path_in_process(
            path, init_globals, return_types="flff"
        )
        if result:
            (
                self._points.array,
                self._facets.array,
                self._vnormals.array,
                *optional,
            ) = result

            if optional:
                print("update uvmap")
                self._uvmap.array = optional[0]
        else:
            warn("Object", self.name, "Multiprocessed Autosmooth failed")

        if debug_flag:
            print(f"#points {self.count_points},  #facets {self.count_facets}")
            print(
                "has vnormals",
                self.has_vnormals(),
                "has uvmap",
                self.has_uvmap(),
            )

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
        tm0 = time.time()
        debug_flag = PARAMS.GetBool("Debug")

        # Initialize
        path = os.path.join(PKGDIR, "rendermesh_mp", "writeobj.py")

        # Transform uvmap
        if self.has_uvmap():
            uvmap = self.uvtransform(*uv_transformation)
            uvmap = ((c.real, c.imag) for c in uvmap)
            uvmap = SharedArray("f", self.count_points, 2, uvmap)
        else:
            uvmap = None

        # Init script globals
        init_globals = {
            "POINTS": self._points.array,
            "FACETS": self._facets.array,
            "VNORMALS": self._vnormals.array,
            "UVMAP": self._uvmap.array,
            "HAS_VNORMALS": self.has_vnormals(),
            "HAS_UVMAP": self.has_uvmap(),
            "MTLFILENAME": mtlfilename,
            "OBJFILE": objfile,
            "OBJNAME": name,
            "MTLNAME": mtlname,
            "SHOWTIME": debug_flag,
            "PYTHON": self.python,
        }

        # Run script
        self._run_path_in_process(path, init_globals)

        if debug_flag:
            tm1 = time.time() - tm0
            print(f"end writing obj file ({tm1})")

    def _run_path_in_process(self, path, init_globals, return_types=None):
        """Run a path in a dedicated process.

        This method is able to launch a multiprocess script, like
        runpy.run_path. However it solves the lack of thread safety of
        'runpy.run_path', by embedding run_path in a dedicated process.
        Please note 'self.python' must have been set. After
        being started, the process is awaited (joined).
        """
        # Synchro objects

        main_conn, sub_conn = connection.Pipe()

        args = (path,)
        init_globals["CONNECTION"] = sub_conn
        init_globals["ENABLE_NUMPY"] = not PARAMS.GetBool("DisableNumpy")
        kwargs = {"init_globals": init_globals, "run_name": "__main__"}

        mp.set_executable(self.python)

        process = mp.Process(
            target=runpy.run_path, args=args, kwargs=kwargs, name="render"
        )
        process.start()
        sentinel = process.sentinel
        result = connection.wait([main_conn, sentinel], 60)
        # Retrieve outputs (into arrays)
        arrays = None
        if result and sentinel not in result:
            msg = main_conn.recv()
            shms = [
                (shared_memory.SharedMemory(name), size) for name, size in msg
            ]
            buffers = [shm.buf[0:size] for shm, size in shms]
            arrays = [
                mp.RawArray(t, b.cast(t))
                for b, t in zip(buffers, return_types)
            ]
            buffers = None  # Otherwise we cannot close shared memory...
            for shm, _ in shms:
                shm.close()
            main_conn.send("terminate")
        elif return_types is not None:
            warn("Object", self.name, "No return from mp module")

        process.join()

        return arrays


class SharedArray:
    """An 2-dimensions array to be shared across multiple processes."""

    def __init__(self, typecode, length, width, initializer=None):
        self._rawarray = mp.RawArray(typecode, length * width)
        self._width = width
        if initializer:
            try:
                self._rawarray[:] = list(
                    itertools.chain.from_iterable(initializer)
                )
            except TypeError:
                self._rawarray[:] = list(
                    itertools.chain.from_iterable(
                        (c.real, c.imag) for c in initializer
                    )
                )

    def __iter__(self):
        iters = [iter(self._rawarray)] * self.width
        return zip(*iters)

    def __getitem__(self, key):
        width = self.width
        return tuple(self._rawarray[key * width : (key + 1) * width])

    def __setitem__(self, key, value):
        width = self.width
        if isinstance(key, slice):

            def scale(arg):
                return arg * width if arg else None

            key = slice(scale(key.start), scale(key.stop), scale(key.step))
            value = list(itertools.chain.from_iterable(value))
            self._rawarray.__setitem__(key, value)
            return
        self._rawarray.__setitem__(key * width, value)

    def __len__(self):
        return len(self._rawarray) // self.width

    @property
    def width(self):
        """Return array width (2nd dim)."""
        return self._width

    @property
    def array(self):
        """Access to underlying array."""
        return self._rawarray

    @array.setter
    def array(self, value):
        self._rawarray = value


# ===========================================================================
#                           Numpy mixin
# ===========================================================================


class RenderMeshNumpyMixin:
    """A mixin class to add Numpy use capabilities to RenderMesh."""

    def _setup_internals(self):
        """Set up internal variables.

        To be overidden by mixins if necessary.
        """
        if PARAMS.GetBool("Debug"):
            tm0 = time.time()
        mesh = self._originalmesh
        points, facets = mesh.Topology
        count_facets = len(facets)
        count_points = len(points)

        if not count_facets:
            # Empty mesh...
            return

        if PARAMS.GetBool("Debug"):
            print(f"{count_points} points, {count_facets} facets")

        points = np.fromiter(
            (x for p in points for x in p),
            dtype=np.float64,
            count=count_points * 3,
        )
        points = points.reshape((-1, 3))
        facets = np.fromiter(
            (x for f in facets for x in f),
            dtype=np.int64,
            count=count_facets * 3,
        )
        facets = facets.reshape((-1, 3))

        if PARAMS.GetBool("Debug"):
            tm1 = time.time() - tm0
            print(f"Setup points & facets {tm1}")

        # `mesh.Facets` is far too slow, so we recompute areas and normals
        # by ourselves.
        # We first compute vector products
        vec1 = points[facets[..., 1]] - points[facets[..., 0]]
        vec2 = points[facets[..., 2]] - points[facets[..., 0]]
        cross = np.cross(vec1, vec2)
        cross_norms = np.linalg.norm(cross, axis=1)

        # We filter out triangles with null area (degenerated...)
        notnull = np.where(cross_norms != 0.0)
        facets = facets[notnull]
        cross = cross[notnull]
        cross_norms = cross_norms[notnull]

        # And we compute normals
        areas = cross_norms / 2
        normals = cross / np.expand_dims(cross_norms, axis=1)

        # Finally we assign to properties
        self._points = points
        self._facets = facets
        self._areas = areas
        self._normals = normals

        self._uvmap = None
        self._vnormals = None

        if PARAMS.GetBool("Debug"):
            tm1 = time.time() - tm0
            print(f"Setup internals {tm1}")

    def has_uvmap(self):
        """Check if object has a uv map."""
        return self._uvmap is not None

    def has_vnormals(self):
        """Check if object has a vertex normals."""
        return self._vnormals is not None

    # TODO uvmap cylinder and sphere

    def _compute_uvmap_cylinder(self):
        """Compute UV map for cylindric case.

        Cylinder axis is supposed to be z.
        """
        super()._compute_uvmap_cylinder()
        self._points = np.asarray(self._points)
        self._facets = np.asarray(self._facets)
        self._normals = np.asarray(self._normals)
        self._areas = np.asarray(self._areas)
        self._uvmap = np.asarray(self._uvmap)

    def _compute_uvmap_sphere(self):
        """Compute UV map for spherical case."""
        super()._compute_uvmap_sphere()
        self._points = np.asarray(self._points)
        self._facets = np.asarray(self._facets)
        self._normals = np.asarray(self._normals)
        self._areas = np.asarray(self._areas)
        self._uvmap = np.asarray(self._uvmap)

    def _compute_uvmap_cube(self):
        """Compute UV map for cubic case - numpy version."""

        debug("Object", self.name, "Compute uvmap (np)")

        time0 = time.time()

        # Set common parameters
        count_facets = self.count_facets
        normals = self._normals
        facets = self._facets
        assert facets.shape[1] == 3
        points = self._points
        areas = self._areas
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
            ],
            dtype=np.float64,
        )
        uvs = np.matmul(
            base_matrices.take(point_colors, axis=0),
            np.expand_dims(centered_points, axis=2),
            axes=[(1, 2), (1, 2), (1, 2)],
        )
        uvs = uvs.squeeze(axis=2)
        uvs /= 1000  # Scale

        # Convert to complex
        uvs.dtype = np.complex128
        uvs = uvs.squeeze(axis=-1)

        # Update attributes
        self._facets = new_facets
        self._points = new_points
        self._uvmap = uvs

        if PARAMS.GetBool("Debug"):
            print("numpy", time.time() - time0)

    def _make_uvmap_positive(self):
        """Make all values in uvmap positive (or zero).

        This is required by LuxCore (procedural textures).
        """
        offset = np.min(np.real(self._uvmap)) + 1j * np.min(
            np.imag(self._uvmap)
        )
        self._uvmap -= offset

    # Filter by normal angles
    @staticmethod
    def _safe_normalize_np(vect_array):
        """Safely normalize an array of vectors."""
        magnitudes = np.sqrt((vect_array**2).sum(-1))
        magnitudes = np.expand_dims(magnitudes, axis=1)
        return np.divide(vect_array, magnitudes, where=magnitudes != 0.0)

    def compute_vnormals(self):
        """Compute vertex normals (numpy version).

        Refresh self._normals. We use an area & angle weighting algorithm."
        """
        debug("Object", self.name, "Compute vertex normals (np)")

        tm0 = time.time()
        if debug_flag := PARAMS.GetBool("Debug"):
            print("compute vnormals Numpy")

        # Prepare parameters
        points = np.array(self._points, dtype="f4")
        normals = np.array(self._normals, dtype="f4")
        areas = np.array(self._areas, dtype="f4")
        facets = np.array(self._facets, dtype="i4")
        triangles = np.take(points, facets, axis=0)
        indices = facets.ravel(order="F")

        if debug_flag:
            print("init", time.time() - tm0)

        def _angles(i, j, k):
            """Compute triangle vertex angles."""
            # Compute normalized vectors
            vec1 = triangles[::, j, ::] - triangles[::, i, ::]
            vec1 = self._safe_normalize_np(vec1)

            vec2 = triangles[::, k, ::] - triangles[::, i, ::]
            vec2 = self._safe_normalize_np(vec2)

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
        point_normals = self._safe_normalize_np(point_normals)

        # self.vnormals = point_normals.tolist()
        self.vnormals = point_normals

        if debug_flag:
            print(time.time() - tm0)

    def _adjacent_facets(self, split_angle=radians(30)):
        """Compute the adjacent facets for each facet of the mesh.

        Returns a list of sets of facet indices (adjacency list).
        Numpy version
        """
        tm0 = time.time()
        if debug_flag := PARAMS.GetBool("Debug"):
            print()
            print(f"compute adjacency lists (np) - {self.count_facets} facets")
            np.set_printoptions(edgeitems=600)

        # Compute mesh edges (assume triangles)
        facets = np.sort(self._facets, axis=1)  # Sort points in each facet
        if debug_flag:
            print("hashes", time.time() - tm0)

        indices = np.arange(len(facets))
        indices = np.tile(indices, 3)

        all_edges_left = np.concatenate(
            (facets[..., 0], facets[..., 0], facets[..., 1])
        )
        all_edges_right = np.concatenate(
            (facets[..., 1], facets[..., 2], facets[..., 2])
        )

        hashes = np.bitwise_or(
            np.left_shift(all_edges_left, 32, dtype=np.int64),
            all_edges_right,
        )

        # At this point, we have a collection of hashed edges ("hashes") like
        # that:
        # facet(i, 0) << 32 | facet(i, 1)
        # facet(i, 0) << 32 | facet(i, 2)
        # facet(i, 1) << 32 | facet(i, 2)
        #
        # where facet(i, j) is the jth point in the ith facet
        # We have to make those hashed edges match between facets to get
        # the connections ("pairs") between facets
        # To do this, we use itertools.groupby

        # Sort hashes and, for each, append the index of the facet
        hashes_indices = np.argsort(hashes)
        hashes = hashes[hashes_indices]
        hashes = np.stack((hashes, hashes_indices % len(facets)), axis=-1)
        if debug_flag:
            print("sorted hashes", time.time() - tm0)

        # Compute hashtable - find connections
        # https://stackoverflow.com/questions/38013778/is-there-any-numpy-group-by-function
        _, unique_indices, unique_counts = np.unique(
            hashes[:, 0], return_index=True, return_counts=True
        )
        hashtable = np.split(
            hashes[:, 1], unique_indices[1:]
        )  # This is array of array
        hashtable = [a for a, n in zip(hashtable, unique_counts) if n == 2]
        if not hashtable:
            if debug_flag:
                print("No edge")
            return np.empty((0, 2), dtype=np.int64)
        hashtable = np.stack(hashtable)

        if debug_flag:
            print(f"all pairs ({len(hashtable)} pairs)", time.time() - tm0)

        # Build adjacency lists
        facet_pairs = np.stack(
            (indices[hashtable[..., 0]], indices[hashtable[..., 1]]), axis=-1
        )

        normals = np.asarray(self._normals)
        vec1 = self._safe_normalize_np(normals[facet_pairs[..., 0]])
        vec2 = self._safe_normalize_np(normals[facet_pairs[..., 1]])

        # Compute dot product. As vectors are normalized, this is cosinus
        # (Clip to avoid precision issues)
        dots = (vec1 * vec2).sum(axis=1).clip(-1.0, 1.0)
        split_angle_cos = cos(split_angle)

        # Compare to split_angle cosinus
        facet_pairs = facet_pairs[np.where(dots > split_angle_cos)]
        if debug_flag:
            print("filtered pairs", time.time() - tm0)

        return facet_pairs

    def _connected_components(self, split_angle=radians(30)):
        """Get all connected components of facets in the mesh.

        Numpy version: this method uses a union-find algorithm, with path
        compression

        Args:
            split_angle -- the angle that breaks adjacency

        Returns:
            a list of tags. Each tag gives the component of the corresponding
                facet
            the number of components
        """
        debug("Object", self.name, "Compute connected components (np)")

        if debug_flag := PARAMS.GetBool("Debug"):
            print()
            print("Connected components (start)")
            tm0 = time.time()
            np.set_printoptions(edgeitems=600)

        edges = self._adjacent_facets(split_angle)
        if debug_flag := PARAMS.GetBool("Debug"):
            print("Adjacent facets", time.time() - tm0)

        nfacets = len(self.facets)
        # Numpy array is slightly slower than list, but it releases GIL...
        fathers = np.full((nfacets,), -1, dtype=np.int64)
        # fathers = [-1] * nfacets

        def getfather(child, _):
            return fathers[child]

        takewhile = itertools.takewhile
        positive = functools.partial(operator.le, 0)
        accumulate_father = functools.partial(
            itertools.accumulate, itertools.repeat(0), getfather
        )
        setter = functools.partial(operator.setitem, fathers)
        getter = functools.partial(operator.getitem, fathers)

        def find_path(element):
            *path, root = takewhile(
                positive, accumulate_father(initial=element)
            )
            return path, root

        def find_and_compress(child):
            # Find
            path, root = find_path(child)

            # Compress (with side-effect)
            _ = [setter(x, root) for x in path]
            # setter(path, root)

            return root

        def union(root1, root2):
            if root1 == root2:
                return

            father1, father2 = getter(root1), getter(root2)
            sumfather = father1 + father2

            if father1 > father2:
                setter(root2, sumfather)
                setter(root1, root2)
            else:
                setter(root1, sumfather)
                setter(root2, root1)

        def union_find(elem1, elem2):
            union(find_and_compress(elem1), find_and_compress(elem2))

        if len(edges):
            vunion_find = np.vectorize(union_find)
            vunion_find(edges[..., 0], edges[..., 1])

        if nfacets:
            vfind_and_compress = np.vectorize(find_and_compress)
            tags = vfind_and_compress(np.arange(nfacets))
        else:
            tags = np.empty(shape=[0], dtype=np.int64)

        if debug_flag:
            print("tags", time.time() - tm0)

        return tags

    def separate_connected_components(self, split_angle=radians(30)):
        """Operate a separation into the mesh between connected components.

        Only points are modified. Facets are kept as-is.

        Args:
            split_angle -- angle threshold, above which 2 adjacents facets
                are considered as non-connected (in radians)
        """
        debug_flag = PARAMS.GetBool("Debug")
        tags = self._connected_components(split_angle)
        tm0 = time.time()
        if debug_flag := PARAMS.GetBool("Debug"):
            print()
            print("distinct tags", len(set(tags)))
            np.set_printoptions(edgeitems=600)

        points = self._points
        facets = self._facets

        # Compute new points
        tags = np.expand_dims(tags, axis=1)
        tags = np.repeat(tags, 3, axis=1)
        tags = np.ravel(tags)
        ravel_facets = np.ravel(facets)
        newpoints = np.column_stack((ravel_facets, tags))
        newpoints, unique_inverse = np.unique(
            newpoints, axis=0, return_inverse=True
        )

        self._points = points[newpoints[..., 0]]

        # Update point indices in facets
        self._facets = np.reshape(unique_inverse, (-1, 3))

        # If necessary, rebuild uvmap
        if self._uvmap is not None:
            self._uvmap = self._uvmap[newpoints[..., 0]]

        if debug_flag:
            print("separate", time.time() - tm0)

    def _scale_points(self, ratio):
        """Scale points with ratio (can be overriden by mixins).

        Numpy version.
        """
        # Make a private copy of points (otherwise, in copied structures
        # like array, points are shared and scale is applied N times)
        self._points = copy.deepcopy(self._points)
        self._points *= ratio

    def compute_tspaces(self):
        """Compute tangent spaces using NumPy."""
        debug("Object", self.name, "Compute tangent spaces 2 (np)")
        tm0 = time.time()
        if debug_flag := PARAMS.GetBool("Debug"):
            print("Start compute_tspaces")

        facets = self._facets  # Shape: (num_facets, 3)
        normals = self._vnormals

        # Compute edge vectors
        points = self._points
        v = (
            points[facets].reshape(-1, 3, 3).transpose(1, 0, 2)
        )  # Shape: (3, num_facets, 3)
        e = np.array([v[1] - v[0], v[2] - v[0]])  # Shape: (2, num_facets, 3)

        # Compute the UV differences
        uvmap = np.column_stack(
            (self._uvmap.real, self._uvmap.imag)
        )  # Shape: (num_facets, 2)
        w = (
            uvmap[facets].reshape(-1, 3, 2).transpose(1, 0, 2)
        )  # Shape: (3, num_facets, 2)
        d = np.array(
            [
                [w[1, ..., 0] - w[0, ..., 0], w[2, ..., 0] - w[0, ..., 0]],
                [w[1, ..., 1] - w[0, ..., 1], w[2, ..., 1] - w[0, ..., 1]],
            ]
        )  # Shape: (2, 2, num_facets)

        # Determinant and filtering
        det = d[0, 0] * d[1, 1] - d[0, 1] * d[1, 0]  # Shape: (num_facets,)
        det_nz = det != 0.0

        # Filter only non-zero determinants
        valid_indices = np.where(det_nz)
        det = det[valid_indices]
        facets = facets[valid_indices]
        e = e[:, valid_indices]
        d = d[:, :, valid_indices]

        # # Normalize factor
        # r = 1.0 / det

        # Combine flattened faces for calculation
        flat_facets = np.ravel(facets)

        # Compute tangents vectors
        sdir = np.column_stack(
            [
                (d[1, 1] * e[0, ..., k] - d[1, 0] * e[1, ..., k]) / det
                for k in range(3)
            ]
        )
        sdir = np.repeat(sdir, 3, axis=0)
        tan1 = np.column_stack(
            [np.bincount(flat_facets, weights=sdir[k]) for k in range(3)]
        )

        tdir = np.column_stack(
            [
                (d[0, 0] * e[1, ..., k] - d[0, 1] * e[0, ..., k]) / det
                for k in range(3)
            ]
        )
        tdir = np.repeat(tdir, 3, axis=0)
        tan2 = np.column_stack(
            [np.bincount(flat_facets, weights=tdir[k]) for k in range(3)]
        )

        # Gram-Schmidt process
        dot_norm_tan1 = (normals * tan1).sum(axis=1, keepdims=True)
        tangents = tan1 - normals * dot_norm_tan1
        tangents = self._safe_normalize_np(tangents)

        # Set handedness
        tangent_signs = np.sign(
            (tan2 * np.cross(normals, tangents)).sum(axis=1)
        )
        tangent_signs[tangent_signs == 0] = 1.0  # Set zero signs to 1

        self._tangents = tangents
        self._tangent_signs = tangent_signs

        if debug_flag:
            print(f"End compute_tspaces: {time.time() - tm0:.6f} seconds")


# ===========================================================================
#                               Helpers
# ===========================================================================


def multiprocessing_enabled(mesh):
    """Check if multiprocessing can be enabled."""
    conditions = (
        PARAMS.GetBool("EnableMultiprocessing"),
        mesh.CountPoints >= PARAMS.GetInt("MultiprocessingThreshold"),
        _find_python(),
    )
    return all(conditions)


def numpy_enabled():
    """Check if multiprocessing can be enabled."""
    conditions = (
        "np" in globals(),
        not PARAMS.GetBool("DisableNumpy"),
    )
    return all(conditions)


def _find_python():
    """Find Python executable."""

    def which(appname):
        app = shutil.which(appname)
        return os.path.abspath(app) if app else None

    if not PARAMS.GetBool("Debug"):
        return which("pythonw") or which("python")
    return which("python")
