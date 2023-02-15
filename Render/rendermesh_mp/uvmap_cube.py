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

from functools import reduce, partial
from itertools import chain

import sys
import os

assert sys.version_info >= (3, 8), "MP requires Python 3.8 or higher"
sys.path.insert(0, os.path.dirname(__file__))

# pylint: disable=wrong-import-position
from vector3d import (
    add,
    sub,
    add_n,
    fmul,
    fdiv,
    barycenter,
    length,
    normal,
    transform,
)
from vector2d import sub as sub2, fdiv as fdiv2
import time  # TODO


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


_list_append = list.append


def colorize(chunk):
    """Attribute "colors" to facets, depending on their orientations.

    Color is an integer in [0,5].
    The color depends on the normal of the triangle, projected to unit cube
    faces.
    This method also computes partial sums for center of gravity.


    Args:
        facets -- An iterable of facets to process

    Returns
        Facet colors (list)
        Centroid of facets (point: 3-float tuple)
        Area sum of facets (float)
    """
    # TODO Put facets in shared

    start, stop = chunk
    facets = [getfacet(i) for i in range(start, stop)]
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

    for ifacet, color in zip(range(start,stop), colors):
        SHARED_FACET_COLORS[ifacet] = color

    return centroid, area


# *****************************************************************************


def update_facets(chunk):
    # Inputs
    start, stop = chunk
    point_map = SHARED_POINT_MAP

    facets = SHARED_FACETS[start * 3 : stop * 3]
    args = [iter(facets)] * 3
    facets = zip(*args)

    colors = SHARED_FACET_COLORS[start:stop]

    result = [
        (
            point_map[facet[0], color],
            point_map[facet[1], color],
            point_map[facet[2], color],
        )
        for facet, color in zip(facets, colors)
    ]
    return result


# *****************************************************************************


def compute_uvmapped_submesh(chunk):
    """Compute a submesh with uvmap from monochrome triangles.

    Args:
        chunk -- a tuple containing:
            cog -- center of gravity (point: 3-float tuple)
            color -- color of the triangles (integer)
            triangles -- monochrome triangles (list of 3-indices elements)

    Returns:
        points -- points of the submesh
        facets -- facets of the submesh
        uvmap -- uvmap of the submesh
    """

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

    uc_map = (
        _uc_xplus,
        _uc_xminus,
        _uc_yplus,
        _uc_yminus,
        _uc_zplus,
        _uc_zminus,
    )

    # TODO Test
    # print(SHARED_POINTS2)

    # Inputs
    # ifacets, facets, colors = [list(i) for i in zip(*colored_facets)]

    # Compute points and facets
    # TODO
    # points = set(chain.from_iterable(facets))
    # points = {p: i for i, p in enumerate(points)}
    # points = SHD_POINTS2
    # facets = [(points[p1], points[p2], points[p3]) for p1, p2, p3 in facets]

    # Compute uvs
    # map_func = uc_map[color]  # TODO
    # cog = map_func(cog)
    uvs = ((uc_map[c], getpoint(p)) for p, c in chunk)
    uvs = [fdiv2(func(sub(point, COG)), 1000) for func, point in uvs]

    # return points, facets, normals, areas, uvs
    return uvs


# *****************************************************************************


# TODO Remove
def offset_facets(offset, facets):
    """Apply (integer) offset to facets indices."""
    return [
        (index1 + offset, index2 + offset, index3 + offset)
        for index1, index2, index3 in facets
    ]


# *****************************************************************************

def init(points, facets, normals, areas, facet_colors):
    """Initialize pool of processes."""
    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    global SHARED_FACETS
    global SHARED_NORMALS
    global SHARED_AREAS
    global SHARED_FACET_COLORS
    SHARED_POINTS = points
    SHARED_FACETS = facets
    SHARED_NORMALS = normals
    SHARED_AREAS = areas
    SHARED_FACET_COLORS = facet_colors
    sys.setswitchinterval(sys.maxsize)


def init2(points, points2, point_colors, facets, facet_colors, cog):
    """Initialize pool of processes."""
    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    SHARED_POINTS = points

    global SHARED_POINT_MAP
    SHARED_POINT_MAP = {
        colored_point: index
        for index, colored_point in enumerate(zip(points2, point_colors))
    }

    global SHARED_FACETS
    SHARED_FACETS = facets

    global SHARED_FACET_COLORS
    SHARED_FACET_COLORS = facet_colors

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
    import shutil
    import itertools
    import time

    tm0 = time.time()

    def tick(msg=""):
        """Print the time (debug purpose)."""
        if showtime:
            print(msg, time.time() - tm0)

    # Only >= 3.8
    def batched(iterable, number):
        "Batch data into lists of length n. The last batch may be shorter."
        # batched('ABCDEFG', 3) --> ABC DEF G
        # from Python itertools documentation...
        iterator = iter(iterable)
        while batch := list(itertools.islice(iterator, number)):
            yield batch

    def grouper(iterable, number, fillvalue=None):
        "Collect data into fixed-length chunks or blocks"
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * number
        return itertools.zip_longest(*args, fillvalue=fillvalue)

    class SharedWrapper:
        """A wrapper for shared objects containing 3-tuples."""

        def __init__(self, seq):
            self.seq = seq

        def __len__(self):
            return len(self.seq) * 3

        def __iter__(self):
            seq = self.seq
            return itertools.islice(
                (x for elem in seq for x in elem), len(seq) * 3
            )

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

    # Prepare shared data
    shd_points = RawArray("d", SharedWrapper(points))
    shd_facets = RawArray("l", SharedWrapper(facets))
    shd_normals = RawArray("d", SharedWrapper(normals))
    shd_areas = RawArray("d", areas)
    shd_facet_colors = RawArray("B", len(facets))
    pool1_args = (shd_points, shd_facets, shd_normals, shd_areas, shd_facet_colors)
    tick("prepare shared")

    # Run
    try:
        # Compute facets colors and center of gravity
        with ctx.Pool(nproc, init, pool1_args) as pool:
            tick("start pool1")
            chunks = (
                (i, min(i + chunk_size, len(facets)))
                for i in range(0, len(facets), chunk_size)
            )
            data = pool.imap(colorize, chunks)  # Keep order
            tick("imap colorize")

            centroids, area_sums = zip(*data)
            centroid = add_n(*centroids)
            area_sum = sum(area_sums)

            # Compute center of gravity
            cog = fdiv(centroid, area_sum)
            # print(cog)  # Debug

        tick("colorize")

        # Update points
        colored_points = {
            (ipoint, color)
            for facet, color in zip(facets, shd_facet_colors)
            for ipoint in facet
        }
        new_points, new_point_colors = zip(*colored_points)
        shd_points2 = RawArray("L", new_points)
        shd_point_colors = RawArray("B", new_point_colors)
        args_pool2 = (shd_points, shd_points2, shd_point_colors, shd_facets, shd_facet_colors, cog)

        tick("points2")

        # Update facets points and compute uv map
        with ctx.Pool(nproc, init2, args_pool2) as pool:
            tick("start pool2")

            # Update facets
            # TODO Use shared mem and ranges
            chunks = (
                (i, min(i + chunk_size, len(facets)))
                for i in range(0, len(facets), chunk_size)
            )
            # chunks = batched(zip(facets, shd_facet_colors), chunk_size)
            facets = sum(pool.imap(update_facets, chunks), [])

            tick("update facets")

            # Compute final mesh and uvmap
            chunks = batched(colored_points, chunk_size)
            uvmap = sum( pool.imap(compute_uvmapped_submesh, chunks), [])
            tick("uv map")

            # Point list
            outpoints = [points[i] for i in new_points]
            tick("new point list")
    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin
        del ctx

    # TODO Do not return normals, areas
    return outpoints, facets, normals, areas, uvmap


# *****************************************************************************

if __name__ == "__main__":
    # Get variables
    # pylint: disable=used-before-assignment
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
    POINTS, FACETS, NORMALS, AREAS, UVMAP = main(
        PYTHON, POINTS, FACETS, NORMALS, AREAS, SHOWTIME
    )
