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
    add_n,
    fmul,
    fdiv,
    barycenter,
    length,
    normal,
    transform,
)
from vector2d import sub as sub2, fdiv as fdiv2


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


def transform_points(matrix, points):
    """Transform points with a transformation matrix 4x4."""
    return [transform(matrix, point) for point in points]

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

    start, stop = chunk
    facets = [getfacet(i) for i in range(start, stop)]
    triangles = (tuple(getpoint(i) for i in facet) for facet in facets)
    data = ((barycenter(t), normal(t)) for t in triangles)
    data = (
        (_intersect_unitcube_face(normal), barycenter, length(normal))
        for barycenter, normal in data
    )
    data = (
        (color, fmul(barycenter, area), area)
        for color, barycenter, area in data
    )
    colors, barys, areas = zip(*data)

    # Compute monochrome sublists

    def facet_reducer(running, new):
        ifacet, color = new
        _list_append(running[color], facets[ifacet])
        return running

    monochrome_facets = reduce(
        facet_reducer,
        enumerate(colors),
        [[], [], [], [], [], []],
    )

    centroid = add_n(*barys)
    # Caveat, this is 2 * area, actually
    # It doesn't matter for our computation, but it could for other cases
    area = sum(areas)
    return monochrome_facets, centroid, area


# *****************************************************************************


def compute_uvmapped_submesh(chunk):
    """Compute a submesh with uvmap from monochrome triangles.

    Args:
        chunk -- a tuple containing:
            cog -- center of gravity (point: 3-float tuple)
            color -- color of the triangles (integer)
            triangles -- monochrome triangles (list of 3-points elements)

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

    # Inputs
    cog, color, facets = chunk

    # Compute points and facets
    points = set(chain.from_iterable(facets))
    points = {p: i for i, p in enumerate(points)}
    facets = [(points[p1], points[p2], points[p3]) for p1, p2, p3 in facets]
    points = [getpoint(i) for i in points.keys()]

    # Compute uvs
    map_func = uc_map[color]
    cog = map_func(cog)
    uvs = [fdiv2(sub2(map_func(p), cog), 1000) for p in points]

    return points, facets, uvs


# *****************************************************************************


def offset_facets(offset, facets):
    """Apply (integer) offset to facets indices."""
    return [
        (index1 + offset, index2 + offset, index3 + offset)
        for index1, index2, index3 in facets
    ]


# *****************************************************************************


def init(points, facets):
    """Initialize pool of processes."""
    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    global SHARED_FACETS
    SHARED_POINTS = points
    SHARED_FACETS = facets
    sys.setswitchinterval(sys.maxsize)


# *****************************************************************************

def main(points, facets, transmat, showtime=False):
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
            return itertools.islice(
                (x for elem in self.seq for x in elem), len(self.seq) * 3
            )

    # Set working directory
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set stdin
    save_stdin = sys.stdin
    sys.stdin = sys.__stdin__

    # Set executable
    executable = shutil.which("pythonw")
    if not executable:
        executable = shutil.which("python")
        if not executable:
            raise RuntimeError("No Python executable")
    # ctx = mp.get_context("spawn")  # Debug
    ctx = mp.get_context()
    ctx.set_executable(executable)

    chunk_size = 20000
    nproc = max(6, os.cpu_count())  # At least, number of faces

    transmat = tuple(grouper(transmat.A, 4))

    shd_points = RawArray("d", SharedWrapper(points))
    shd_facets = RawArray("l", SharedWrapper(facets))
    tick("prepare shared")

    # Run
    try:
        with ctx.Pool(nproc, init, (shd_points, shd_facets)) as pool:
            tick("start pool")
            # Compute colors, and partial sums for center of gravity
            chunks = (
                (i, min(i + chunk_size, len(facets)))
                for i in range(0, len(facets), chunk_size)
            )
            data = pool.imap_unordered(colorize, chunks)
            tick("colorize")

            # Concatenate/reduce processed chunks
            def chunk_reducer(running, new):
                """Reducer for colors chunks."""
                running_facets, running_centroid, running_area_sum = running
                facets, centroid, area_sum = new
                for i, j in zip(running_facets, facets):
                    i += j
                running_centroid = add(running_centroid, centroid)
                running_area_sum += area_sum
                return running_facets, running_centroid, running_area_sum

            init_data = ([[], [], [], [], [], []], (0.0, 0.0, 0.0), 0.0)
            data = reduce(chunk_reducer, data, init_data)
            monochrome_facets, centroid, area_sum = data
            tick("reduce colorize")

            # Compute center of gravity
            cog = fdiv(centroid, area_sum)
            # print(cog)  # Debug

            tick("sublists")

            # print([len(t) for t in monochrome_facets])  # Debug

            # Compute final mesh and uvmap
            chunks = (
                (cog, color, facets)
                for color, facets in enumerate(monochrome_facets)
            )
            submeshes = pool.imap_unordered(compute_uvmapped_submesh, chunks)
            points, facets, uvmap = [], [], []
            for subpoints, subfacets, subuv in submeshes:
                offset = len(points)
                points += subpoints

                chunks = batched(subfacets, chunk_size)
                offset_function = partial(offset_facets, offset)
                facets += chain.from_iterable(
                    pool.imap(offset_function, chunks)
                )

                uvmap += subuv

            tick("final mesh")

            # Transform points (with transmat)
            _transform_points = partial(transform_points, transmat)
            output = pool.imap(_transform_points, batched(points, chunk_size))
            points = sum(output, [])

            tick("transform")

    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin
    return points, facets, uvmap


# *****************************************************************************

if __name__ == "__main__":
    # Get variables
    # pylint: disable=used-before-assignment
    try:
        FACETS
    except NameError:
        FACETS = []

    try:
        POINTS
    except NameError:
        POINTS = []

    try:
        UVMAP
    except NameError:
        UVMAP = []

    try:
        TRANSMAT
    except NameError:
        TRANSMAT = None

    try:
        SHOWTIME
    except NameError:
        SHOWTIME = False

    SHOWTIME = True  # Debug
    POINTS, FACETS, UVMAP = main(POINTS, FACETS, TRANSMAT, SHOWTIME)
