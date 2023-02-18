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

"""Script for cubic uvmap computation in multiprocessing mode."""

import sys
import os
import itertools

sys.path.insert(0, os.path.dirname(__file__))
# pylint: disable=wrong-import-position
from vector3d import (
    sub,
    add_n,
    fmul,
    fdiv,
    barycenter,
)
from vector2d import fdiv as fdiv2

assert sys.version_info >= (3, 8), "MP requires Python 3.8 or higher"


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

    for ifacet, color in zip(range(start, stop), colors):
        SHARED_FACET_COLORS[ifacet] = color

    return centroid, area


# *****************************************************************************


def update_facets(chunk):
    """Update point indices in facets.

    To be run once points have been split by color.
    """
    # Inputs
    start, stop = chunk
    point_map = SHARED_POINT_MAP
    facets = SHARED_FACETS
    colors = SHARED_FACET_COLORS

    for ifacet in range(start, stop):
        color = colors[ifacet]
        facets[ifacet * 3 + 0] = point_map[facets[ifacet * 3 + 0], color]
        facets[ifacet * 3 + 1] = point_map[facets[ifacet * 3 + 1], color]
        facets[ifacet * 3 + 2] = point_map[facets[ifacet * 3 + 2], color]


# *****************************************************************************


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
    start, stop = chunk
    colored_points = SHARED_COLORED_POINTS[start * 2 : stop * 2]
    colored_points = [iter(colored_points)] * 2
    colored_points = zip(*colored_points)

    uvs = ((UC_MAP[c], getpoint(p)) for p, c in colored_points)
    uvs = [fdiv2(func(sub(point, COG)), 1000) for func, point in uvs]

    for index, uv in zip(range(start, stop), uvs):
        SHARED_UVMAP[index * 2], SHARED_UVMAP[index * 2 + 1] = uv


# *****************************************************************************


def init(shared):
    """Initialize pool of processes #1."""
    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    global SHARED_FACETS
    global SHARED_NORMALS
    global SHARED_AREAS
    global SHARED_FACET_COLORS
    SHARED_POINTS = shared["points"]
    SHARED_FACETS = shared["facets"]
    SHARED_NORMALS = shared["normals"]
    SHARED_AREAS = shared["areas"]
    SHARED_FACET_COLORS = shared["facet_colors"]
    sys.setswitchinterval(sys.maxsize)


def init2(shared, cog):
    """Initialize pool of processes #2."""
    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    SHARED_POINTS = shared["points"]

    global SHARED_POINT_MAP
    iterator = [iter(shared["colored_points"])] * 2
    iterator = zip(*iterator)
    SHARED_POINT_MAP = {
        colored_point: index for index, colored_point in enumerate(iterator)
    }

    global SHARED_COLORED_POINTS
    SHARED_COLORED_POINTS = shared["colored_points"]

    global SHARED_FACETS
    SHARED_FACETS = shared["facets"]

    global SHARED_FACET_COLORS
    SHARED_FACET_COLORS = shared["facet_colors"]

    global SHARED_UVMAP
    SHARED_UVMAP = shared["uvmap"]

    global COG
    COG = cog

    sys.setswitchinterval(sys.maxsize)


# *****************************************************************************


def main(python, points, facets, normals, areas, showtime=False):
    """Entry point for __main__.

    This code executes in main process.
    Keeping this code out of global scope makes all local objects to be freed
    at the end of the function and thus avoid memory leaks.
    """
    # pylint: disable=import-outside-toplevel
    # pylint: disable=too-many-locals
    import multiprocessing as mp
    from multiprocessing.sharedctypes import RawArray
    import itertools
    import time

    def tick(msg=""):
        """Print the time (debug purpose)."""
        if showtime:
            print(msg, time.time() - tm0)

    tm0 = time.time()
    tick(f"start uv computation: {len(points)} points, {len(facets)} facets ")

    def grouper(iterable, number, fillvalue=None):
        "Collect data into fixed-length chunks or blocks"
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * number
        return itertools.zip_longest(*args, fillvalue=fillvalue)

    def make_chunks(chunk_size, length):
        return (
            (i, min(i + chunk_size, length))
            for i in range(0, length, chunk_size)
        )

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
            "points": ctx.RawArray("d", SharedWrapper(points, 3)),
            "facets": ctx.RawArray("l", SharedWrapper(facets, 3)),
            "normals": ctx.RawArray("d", SharedWrapper(normals, 3)),
            "areas": ctx.RawArray("d", areas),
            "facet_colors": ctx.RawArray("B", len(facets)),
        }
        tick("prepare shared")
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool1")
            chunks = make_chunks(chunk_size, len(facets))
            data = pool.imap_unordered(colorize, chunks)

            centroids, area_sums = zip(*data)
            centroid = add_n(*centroids)
            area_sum = sum(area_sums)

            # Compute center of gravity
            cog = fdiv(centroid, area_sum)
            # print(cog)  # Debug
        del shared["normals"]
        del shared["areas"]
        tick("colorize")

        # Update points
        colored_points = {
            (ipoint, color)
            for facet, color in zip(facets, shared["facet_colors"])
            for ipoint in facet
        }
        tick("new points")

        # Update facets points and compute uv map
        shared["colored_points"] = ctx.RawArray("L", SharedWrapper(colored_points, 2))
        shared["uvmap"] = ctx.RawArray("d", len(colored_points) * 2)
        tick("prepare shared")
        with ctx.Pool(nproc, init2, (shared, cog)) as pool:
            tick("start pool2")

            # Update facets
            chunks = make_chunks(chunk_size, len(facets))
            pool.map(update_facets, chunks)
            facets = list(grouper(shared["facets"], 3))

            tick("update facets")

            # Compute uvmap
            chunks = make_chunks(chunk_size, len(colored_points))
            pool.map(compute_uvmap, chunks)
            uvmap = list(grouper(shared["uvmap"], 2))
            tick("uv map")

            # Point list
            newpoints = [
                points[i]
                for i in itertools.islice(shared["colored_points"], 0, None, 2)
            ]
            tick("new point list")

    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin

    return newpoints, facets, uvmap


# *****************************************************************************

if __name__ == "__main__":
    # Get variables
    # pylint: disable=used-before-assignment
    try:
        PYTHON
    except NameError:
        PYTHON = ""

    try:
        POINTS
    except NameError:
        POINTS = []

    try:
        FACETS
    except NameError:
        FACETS = []

    try:
        NORMALS
    except NameError:
        NORMALS = []

    try:
        AREAS
    except NameError:
        AREAS = []

    try:
        UVMAP
    except NameError:
        UVMAP = []

    try:
        SHOWTIME
    except NameError:
        SHOWTIME = False

    SHOWTIME = True  # Debug
    POINTS, FACETS, UVMAP = main(
        PYTHON, POINTS, FACETS, NORMALS, AREAS, SHOWTIME
    )
