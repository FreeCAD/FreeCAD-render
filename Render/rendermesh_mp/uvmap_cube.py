# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2022 Howetuft <howetuft@gmail.com>                      *
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

"""Script for cubic uvmap computation in multiprocessing mode."""

# pylint: disable=possibly-used-before-assignment

import sys
import os
import traceback

try:
    import numpy as np

    USE_NUMPY = True
except ModuleNotFoundError:
    USE_NUMPY = False

sys.path.insert(0, os.path.dirname(__file__))
# pylint: disable=wrong-import-position
from vector3d import (
    sub,
    add_n,
    fmul,
    fdiv,
    barycenter,
)


# Vocabulary:
# Point: a 3-tuple of float designing a point in 3D
# Facet: a 3-tuple of indices (integer) pointing to 3 points in a point list
# Triangle: a 3-tuple of points (see above)
# Mesh: a pair (point list, facet list)
# Color: an integer associated to a facet/triangle, in order to separate
#   submeshes
# Chunk: a sliced sublist, to be processed in parallel way


# *****************************************************************************


def getpoint(idx):
    """Get a point from its index in the shared memory."""
    idx *= 3
    return SHARED_POINTS[idx], SHARED_POINTS[idx + 1], SHARED_POINTS[idx + 2]


def getfacet(idx):
    """Get a facet from its index in the shared memory."""
    idx *= 3
    return SHARED_FACETS[idx], SHARED_FACETS[idx + 1], SHARED_FACETS[idx + 2]


def getnormal(idx):
    """Get a normal from its index in the shared memory."""
    idx *= 3
    return (
        SHARED_NORMALS[idx],
        SHARED_NORMALS[idx + 1],
        SHARED_NORMALS[idx + 2],
    )


def getarea(idx):
    """Get a normal from its index in the shared memory."""
    return SHARED_AREAS[idx]


# *****************************************************************************


def _intersect_unitcube_face(direction):
    """Get the face of the unit cube intersected by a line from origin.

    Args:
        direction -- The directing vector for the intersection line
        (a 3-float sequence)

    Returns:
        A face from the unit cube (_UnitCubeFaceEnum)
    """
    dirx, diry, dirz = direction
    vec = (
        (abs(dirx), 0, dirx < 0),
        (abs(diry), 2, diry < 0),
        (abs(dirz), 4, dirz < 0),
    )
    _, idx1, idx2 = max(vec)
    return idx1 + int(idx2)


def colorize(chunk):
    """Attribute color to facets in chunk."""
    if USE_NUMPY:
        return colorize_np(chunk)

    return colorize_std(chunk)


def colorize_std(chunk):
    """Attribute "colors" to facets, depending on their orientations.

    Color is an integer in [0,5].
    The color depends on the normal of the triangle, projected to unit cube
    faces.
    This method also computes partial sums for center of gravity.
    The colors are directly set in shared memory.


    Args:
        chunk -- a pair of facet indices (start, stop)

    Returns
        Centroid of facets (point: 3-float tuple)
        Area sum of facets (float)
    """
    start, stop = chunk
    facets = (getfacet(i) for i in range(start, stop))
    normals = (getnormal(i) for i in range(start, stop))
    areas = [getarea(i) for i in range(start, stop)]
    triangles = (tuple(getpoint(i) for i in facet) for facet in facets)

    data = (
        (barycenter(t), n, a) for t, n, a in zip(triangles, normals, areas)
    )
    data = (
        (_intersect_unitcube_face(normal), barycenter, area)
        for barycenter, normal, area in data
    )
    data = (
        (color, fmul(barycenter, area)) for color, barycenter, area in data
    )
    colors, barys = zip(*data)

    centroid = add_n(*barys)
    area = sum(areas)

    SHARED_FACET_COLORS[start:stop] = list(colors)

    return centroid, area


def colorize_np(chunk):
    """Attribute color to facets in chunk - numpy version."""
    # Set common parameters
    start, stop = chunk

    normals = SHARED_NORMALS_NP[start:stop,]

    facets = SHARED_FACETS_NP[start:stop,]

    areas = SHARED_AREAS_NP[start:stop]

    triangles = np.take(SHARED_POINTS_NP, facets, axis=0)

    # Compute facet colors
    # Color is made of 2 terms:
    # First term: max of absolute coordinates of normals
    # Second term: sign of corresponding coordinate
    first_term = np.abs(normals)
    first_term = np.argmax(first_term, axis=1)  # Maximal coordinate
    first_term = np.expand_dims(first_term, axis=1)
    second_term = np.less(normals, np.zeros((stop - start, 3))).astype(int)
    second_term = np.take_along_axis(second_term, first_term, axis=1)
    facet_colors = first_term * 2 + second_term
    facet_colors = facet_colors.ravel()

    # Update facet colors
    np.copyto(
        SHARED_FACET_COLORS_NP[start:stop], facet_colors, casting="unsafe"
    )

    # Compute center of gravity (triangle cogs weighted by triangle areas)
    weighted_triangle_cogs = (
        np.add.reduce(triangles, 1) * areas[:, np.newaxis] / 3
    )
    centroid = np.sum(weighted_triangle_cogs, axis=0).tolist()
    area = float(np.sum(areas))

    return centroid, area


# *****************************************************************************


def update_facets(chunk):
    """Update point indices in facets.

    To be run once points have been split by color.
    """
    # Inputs
    start, stop = chunk

    # Point map
    # pylint: disable=global-variable-undefined
    global SHARED_POINT_MAP
    if SHARED_POINT_MAP is None:
        length = SHARED_COLORED_POINTS_LEN.value
        iterator = [iter(SHARED_COLORED_POINTS[0:length])] * 2
        iterator = zip(*iterator)
        SHARED_POINT_MAP = {
            colored_point: index
            for index, colored_point in enumerate(iterator)
        }

    # Aliases
    point_map = SHARED_POINT_MAP
    facets = SHARED_FACETS
    colors = SHARED_FACET_COLORS

    for ifacet in range(start, stop):
        color = colors[ifacet]
        index = ifacet * 3
        facets[index] = point_map[facets[index], color]
        facets[index + 1] = point_map[facets[index + 1], color]
        facets[index + 2] = point_map[facets[index + 2], color]


# *****************************************************************************


def _uc_xplus(point):
    """Unit cube - xplus case."""
    _, pt1, pt2 = point
    return complex(pt1, pt2)


def _uc_xminus(point):
    """Unit cube - xminus case."""
    _, pt1, pt2 = point
    return complex(-pt1, pt2)


def _uc_yplus(point):
    """Unit cube - yplus case."""
    pt0, _, pt2 = point
    return complex(-pt0, pt2)


def _uc_yminus(point):
    """Unit cube - yminus case."""
    pt0, _, pt2 = point
    return complex(pt0, pt2)


def _uc_zplus(point):
    """Unit cube - zplus case."""
    pt0, pt1, _ = point
    return complex(pt0, pt1)


def _uc_zminus(point):
    """Unit cube - zminus case."""
    pt0, pt1, _ = point
    return complex(pt0, -pt1)


UC_MAP = (
    _uc_xplus,
    _uc_xminus,
    _uc_yplus,
    _uc_yminus,
    _uc_zplus,
    _uc_zminus,
)


def compute_uvmap(chunk):
    """Compute uvmap.

    Args:
        chunk -- a iterable of pairs containing:
            color -- color of the point (integer)
            point -- point index (integer)

    Returns:
        uvmap
    """
    if USE_NUMPY:
        return compute_uvmap_np(chunk)

    return compute_uvmap_std(chunk)


def compute_uvmap_std(chunk):
    """Compute uvmap.

    Args:
        chunk -- a iterable of pairs containing:
            color -- color of the point (integer)
            point -- point index (integer)

    Returns:
        uvmap
    """
    start, stop = chunk
    colored_points = SHARED_COLORED_POINTS[start * 2 : stop * 2]
    colored_points = [iter(colored_points)] * 2
    colored_points = zip(*colored_points)
    cog = tuple(SHARED_COG)

    uvs = ((UC_MAP[c], getpoint(p)) for p, c in colored_points)
    uvs = (func(sub(point, cog)) / 1000 for func, point in uvs)

    for index, uv_ in zip(range(start, stop), uvs):
        SHARED_UVMAP[index * 2] = uv_.real
        SHARED_UVMAP[index * 2 + 1] = uv_.imag


if USE_NUMPY:
    BASE_MATRICES = np.array(
        [
            [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            [[0.0, -1.0, 0.0], [0.0, 0.0, 1.0]],
            [[-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0]],
        ]
    )


def compute_uvmap_np(chunk):
    """Compute uvmap (numpy).

    Args:
        chunk -- a iterable of pairs containing:
            color -- color of the point (integer)
            point -- point index (integer)

    Returns:
        uvmap
    """
    # Unpack args
    start, stop = chunk

    # Prepare chunk
    point_indices = SHARED_COLORED_POINTS_NP[start:stop, 0].astype(np.int64)
    points = np.take(SHARED_POINTS_NP, point_indices, axis=0)
    point_colors = SHARED_COLORED_POINTS_NP[start:stop, 1].astype(np.int64)

    # Compute uvmap
    # Center points to center of gravity.
    # Apply linear transformation to point coordinates.
    # The transformation depends on the point color.
    centered_points = points - SHARED_COG_NP
    uvs = np.matmul(
        BASE_MATRICES.take(point_colors, axis=0),
        np.expand_dims(centered_points, axis=2),
        axes=[(1, 2), (1, 2), (1, 2)],
    )
    uvs = uvs.squeeze(axis=2)
    uvs /= 1000  # Scale

    np.copyto(SHARED_UVMAP_NP[start:stop], uvs, casting="unsafe")


# *****************************************************************************


def init(shared):
    """Initialize pool of processes."""

    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    SHARED_POINTS = shared["points"]

    global SHARED_FACETS
    SHARED_FACETS = shared["facets"]

    global SHARED_NORMALS
    SHARED_NORMALS = shared["normals"]

    global SHARED_AREAS
    SHARED_AREAS = shared["areas"]

    global SHARED_COG
    SHARED_COG = shared["cog"]

    global SHARED_FACET_COLORS
    SHARED_FACET_COLORS = shared["facet_colors"]

    global SHARED_COLORED_POINTS
    SHARED_COLORED_POINTS = shared["colored_points"]

    global SHARED_COLORED_POINTS_LEN
    SHARED_COLORED_POINTS_LEN = shared["colored_points_len"]

    global SHARED_POINT_MAP
    SHARED_POINT_MAP = None

    global SHARED_UVMAP
    SHARED_UVMAP = shared["uvmap"]

    # pylint: disable=global-statement
    global USE_NUMPY

    if USE_NUMPY := USE_NUMPY and shared["enable_numpy"]:
        global SHARED_NORMALS_NP
        SHARED_NORMALS_NP = np.ctypeslib.as_array(SHARED_NORMALS)
        SHARED_NORMALS_NP.shape = (-1, 3)

        global SHARED_FACETS_NP
        SHARED_FACETS_NP = np.ctypeslib.as_array(SHARED_FACETS)
        SHARED_FACETS_NP.shape = (-1, 3)

        global SHARED_AREAS_NP
        SHARED_AREAS_NP = np.ctypeslib.as_array(SHARED_AREAS)

        global SHARED_POINTS_NP
        SHARED_POINTS_NP = np.ctypeslib.as_array(SHARED_POINTS)
        SHARED_POINTS_NP.shape = (len(SHARED_POINTS) // 3, 3)

        global SHARED_FACET_COLORS_NP
        SHARED_FACET_COLORS_NP = np.ctypeslib.as_array(SHARED_FACET_COLORS)

        global SHARED_COLORED_POINTS_NP
        SHARED_COLORED_POINTS_NP = np.ctypeslib.as_array(SHARED_COLORED_POINTS)
        SHARED_COLORED_POINTS_NP.shape = (len(SHARED_COLORED_POINTS) // 2, 2)

        global SHARED_COG_NP
        SHARED_COG_NP = np.ctypeslib.as_array(SHARED_COG)

        global SHARED_UVMAP_NP
        SHARED_UVMAP_NP = np.ctypeslib.as_array(SHARED_UVMAP)
        SHARED_UVMAP_NP.shape = (len(SHARED_UVMAP) // 2, 2)


# *****************************************************************************


# pylint: disable=too-many-arguments
def main(
    python,
    points,
    facets,
    normals,
    areas,
    showtime,
    enable_numpy,
    out_points,
    out_point_count,
    out_facets,
    out_uvmap,
):
    """Entry point for __main__.

    This code executes in main process.
    Keeping this code out of global scope makes all local objects to be freed
    at the end of the function and thus avoid memory leaks.
    """
    # pylint: disable=import-outside-toplevel
    # pylint: disable=too-many-locals
    import multiprocessing as mp
    import itertools
    import time

    count_facets = len(facets) // 3
    count_points = len(points) // 3

    tm0 = time.time()
    if showtime:
        msg = (
            f"start uv computation: {count_points} points, "
            f"{count_facets} facets"
        )
        print(msg)

    def tick(msg=""):
        """Print the time (debug purpose)."""
        if showtime:
            print(msg, time.time() - tm0)

    def make_chunks(chunk_size, length):
        return (
            (i, min(i + chunk_size, length))
            for i in range(0, length, chunk_size)
        )

    def run_unordered(pool, function, iterable):
        imap = pool.imap_unordered(function, iterable)
        for _ in imap:
            pass

    class SharedWrapper:
        """A wrapper for shared objects containing tuples."""

        def __init__(self, seq, tuple_length):
            self.seq = seq
            self.tuple_length = tuple_length

        def __len__(self):
            return len(self.seq) * self.tuple_length

        def __iter__(self):
            seq = self.seq
            return itertools.chain.from_iterable(seq)

    # Set working directory
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set stdin
    save_stdin = sys.stdin
    sys.stdin = sys.__stdin__

    # Set executable
    ctx = mp.get_context("spawn")
    ctx.set_executable(python)

    chunk_size = 20000
    nproc = os.cpu_count()

    try:
        # Compute facets colors and center of gravity
        shared = {
            "points": points,
            "facets": facets,
            "normals": normals,
            "areas": areas,
            "cog": ctx.RawArray("f", 3),
            "facet_colors": ctx.RawArray("B", count_facets),
            "colored_points": ctx.RawArray("L", count_points * 2 * 6),
            "colored_points_len": ctx.RawValue("l"),
            "uvmap": ctx.RawArray("f", count_points * 2 * 6),
            "enable_numpy": enable_numpy,
        }
        tick("prepare shared")
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")
            chunks = make_chunks(chunk_size, count_facets)
            data = pool.imap_unordered(colorize, chunks)

            centroids, area_sums = zip(*data)
            centroid = add_n(*centroids)
            area_sum = sum(area_sums)

            # Compute center of gravity
            cog = fdiv(centroid, area_sum)
            shared["cog"][:] = cog
            tick("colorize")

            # Update points
            fcol = shared["facet_colors"]
            tiled_fcol = itertools.chain.from_iterable(zip(fcol, fcol, fcol))
            colored_points = set(zip(facets, tiled_fcol))
            colored_points_len = len(colored_points)
            tick(f"new points ({colored_points_len} pts)")

            # Update facets points
            wrapper = SharedWrapper(colored_points, 2)
            shared["colored_points"][0 : len(wrapper)] = list(wrapper)
            shared["colored_points_len"].value = len(wrapper)

            # Update facets
            chunks = make_chunks(chunk_size, count_facets)
            run_unordered(pool, update_facets, chunks)
            out_facets[::] = shared["facets"]
            tick("update facets")

            # Compute uvmap
            chunks = make_chunks(chunk_size, len(colored_points))
            run_unordered(pool, compute_uvmap, chunks)
            out_uvmap[: len(shared["uvmap"])] = shared["uvmap"]
            tick("uv map")

            # Recompute point list
            newpoints = [
                coord
                for i, _ in colored_points
                for coord in points[3 * i : 3 * i + 3]
            ]
            out_points[: colored_points_len * 3] = newpoints
            tick("new point list")
    except Exception as exc:
        print(traceback.format_exc())
        input("Press Enter to continue...")
        raise exc
    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin

    out_point_count.value = colored_points_len


# *****************************************************************************

if __name__ == "__main__":
    # pylint: disable=used-before-assignment
    main(
        PYTHON,
        POINTS,
        FACETS,
        NORMALS,
        AREAS,
        SHOWTIME,
        ENABLE_NUMPY,
        OUT_POINTS,
        OUT_POINT_COUNT,
        OUT_FACETS,
        OUT_UVMAP,
    )

    # Clean
    PYTHON = None
    POINTS = None
    FACETS = None
    NORMALS = None
    AREAS = None
    SHOWTIME = None
    ENABLE_NUMPY = None
    OUT_POINTS = None
    OUT_POINT_COUNT = None
    OUT_FACETS = None
    OUT_UVMAP = None
    BASE_MATRICES = None
