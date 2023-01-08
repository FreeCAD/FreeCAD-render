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
from math import sqrt
from operator import mul as op_mul, sub as op_sub


# Vocabulary:
# Point: a 3-tuple of float designing a point in 3D
# Facet: a 3-tuple of indices (integer) pointing to 3 points in a point list
# Triangle: a 3-tuple of points (see above)
# Mesh: a pair (point list, facet list)
# Color: an integer associated to a facet/triangle, in order to separate
#   submeshes
# Chunk: a sliced sublist, to be processed in parallel way


def transform_points(matrix, points):
    """Transform points with a transformation matrix 4x4."""
    return [transform(matrix, point) for point in points]


def colorize(triangles):
    """Attribute "colors" to triangles, depending on their orientations.

    Color is an integer in [0,5].
    The color depends on the normal of the triangle, projected to unit cube
    faces.
    This method also computes partial sums for center of gravity.


    Args:
        triangles -- An iterable of triangles to process

    Returns
        Facet colors (list)
        Centroid of facets (point: 3-float tuple)
        Area sum of facets (float)
    """

    def intersect_unitcube_face(direction):
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

    # https://stackoverflow.com/questions/48918530/how-to-compute-the-centroid-of-a-mesh-with-triangular-faces
    data = ((barycenter(t), normal(t)) for t in triangles)

    def reducer(running, new):
        colors, centroid, area_sum = running
        bary, norm = new

        # Caveat, this is 2 * area, actually
        # It doesn't matter for our computation, but it could for other cases
        area = length(norm)

        colors.append(intersect_unitcube_face(norm))
        centroid = add(centroid, fmul(bary, area))
        area_sum += area

        return colors, centroid, area_sum

    init_reducer = (bytearray(0), (0.0, 0.0, 0.0), 0.0)
    result = reduce(reducer, data, init_reducer)
    return result  # triangle colors, centroid, area sum


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
    cog, color, triangles = chunk

    # Compute points and facets
    points = set(chain.from_iterable(triangles))
    points = {p: i for i, p in enumerate(points)}
    facets = [(points[p1], points[p2], points[p3]) for p1, p2, p3 in triangles]
    points = list(points.keys())

    # Compute uvs
    map_func = uc_map[color]
    cog = map_func(cog)
    uvs = [fdiv(sub(map_func(p), cog), 1000) for p in points]

    return points, facets, uvs


# *****************************************************************************


def offset_facets(offset, facets):
    """Apply (integer) offset to facets indices."""
    return [
        (index1 + offset, index2 + offset, index3 + offset)
        for index1, index2, index3 in facets
    ]


# *****************************************************************************


def add(*vectors):
    """Add 2 or more vectors."""
    return tuple(sum(x) for x in zip(*vectors))


def sub(vec1, vec2):
    """Substract 2 vectors."""
    return tuple(map(op_sub, vec1, vec2))


def fmul(vec, flt):
    """Multiply a vector by a float."""
    return tuple(x * flt for x in vec)


def fdiv(vec, flt):
    """Divide a vector by a float."""
    return tuple(x / flt for x in vec)


def barycenter(polygon):
    """Compute isobarycenter of a polygon."""
    return fdiv(add(*polygon), len(polygon))


def length(vec):
    """Compute vector length."""
    return sqrt(sum(x**2 for x in vec))


def normal(triangle):
    """Compute the normal of a triangle."""
    # (p1 - p0) ^ (p2 - p0)
    point0, point1, point2 = triangle
    vec1 = sub(point1, point0)
    vec2 = sub(point2, point0)
    res = (
        vec1[1] * vec2[2] - vec1[2] * vec2[1],
        vec1[2] * vec2[0] - vec1[0] * vec2[2],
        vec1[0] * vec2[1] - vec1[1] * vec2[0],
    )
    return res


def dot(vec1, vec2):
    """Dot product."""
    return sum(map(op_mul, vec1, vec2))


def transform(matrix, vec):
    """Transform a 3D vector with a transformation matrix 4x4."""
    vec2 = (*vec, 1)
    return tuple(dot(line, vec2) for line in matrix[:-1])


# *****************************************************************************


def main(points, facets, transmat):
    """Entry point for __main__.

    This code executes in main process.
    Keeping this code out of global scope makes all local objects to be freed
    at the end of the function and thus avoid memory leaks.
    """
    # pylint: disable=import-outside-toplevel
    # pylint: disable=too-many-locals
    import multiprocessing as mp
    import os
    import sys
    import shutil
    import itertools
    import time

    tm0 = time.time()

    # Only >= 3.8
    def batched(iterable, number):
        "Batch data into lists of length n. The last batch may be shorter."
        # batched('ABCDEFG', 3) --> ABC DEF G
        # from Python itertools documentation...
        iterator = iter(iterable)
        while batch := list(itertools.islice(iterator, number)):
            yield batch

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
    ctx = mp.get_context("spawn")
    ctx.set_executable(executable)

    chunk_size = 20000
    nproc = max(6, os.cpu_count())  # At least, number of faces

    # TODO Move elsewhere
    def grouper(iterable, number, fillvalue=None):
        "Collect data into fixed-length chunks or blocks"
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * number
        return itertools.zip_longest(*args, fillvalue=fillvalue)

    transmat = tuple(grouper(transmat.A, 4))

    # Run
    try:
        with ctx.Pool(nproc) as pool:
            print("start pool", time.time() - tm0)
            # Compute colors, and partial sums for center of gravity
            triangles = [tuple(points[i] for i in facet) for facet in facets]
            print("compute triangles", time.time() - tm0)
            chunks = batched(triangles, chunk_size)
            data = pool.map(colorize, chunks)
            print("colorize", time.time() - tm0)

            # Concatenate/reduce processed chunks
            def chunk_reducer(running, new):
                """Reducer for colors chunks."""
                running_colors, running_centroid, running_area_sum = running
                colors, centroid, area_sum = new
                running_centroid = add(running_centroid, centroid)
                running_area_sum += area_sum
                running_colors += colors
                return running_colors, running_centroid, running_area_sum

            init_data = (bytearray(), (0.0, 0.0, 0.0), 0.0)
            data = reduce(chunk_reducer, data, init_data)
            triangle_colors, centroid, area_sum = data
            print("reduce colorize", time.time() - tm0)

            # Compute center of gravity
            cog = fdiv(centroid, area_sum)

            # Generate 6 sublists of monochrome triangles
            # TODO merge with previous computation?
            def triangle_reducer(running, new):
                itriangle, color = new
                running[color].append(triangles[itriangle])
                return running

            init_monochrome_triangles = [[], [], [], [], [], []]
            monochrome_triangles = reduce(
                triangle_reducer,
                enumerate(triangle_colors),
                init_monochrome_triangles,
            )
            print("sublists", time.time() - tm0)
            # print([len(t) for t in monochrome_triangles])  # Debug

            # Compute final mesh and uvmap
            chunks = (
                (cog, color, triangles)
                for color, triangles in enumerate(monochrome_triangles)
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

            print("final mesh", time.time() - tm0)

            # Transform points (with transmat)
            _transform_points = partial(transform_points, transmat)
            output = pool.imap(_transform_points, batched(points, chunk_size))
            points = sum(output, [])

            print("transform", time.time() - tm0)

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

    POINTS, FACETS, UVMAP = main(POINTS, FACETS, TRANSMAT)
