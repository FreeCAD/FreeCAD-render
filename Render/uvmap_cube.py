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

from functools import reduce, partial
from itertools import chain, islice
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
    return [transform(matrix, point) for point in points]


def colorize(triangles):
    """Attribute "colors" to triangles, depending on their orientations.

    Color is an integer in [0,5].
    The color depends on the normal of the triangle, projected to unit cube faces.
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

    # https://stackoverflow.com/questions/48918530/how-to-compute-the-centroid-of-a-mesh-with-triangular-faces
    data = ((barycenter(t), normal(t)) for t in triangles)

    def reducer(x, y):
        colors, centroid, area_sum = x
        barycenter, normal = y

        area = 0.5 * length(normal)

        colors.append(intersect_unitcube_face(normal))
        centroid = add(centroid, fmul(barycenter, area))
        area_sum += area

        return colors, centroid, area_sum

    init_reducer = (bytearray(0), (0.0, 0.0, 0.0), 0.0)
    result = reduce(reducer, data, init_reducer)
    return result  # triangle colors, centroid, area sum


# TODO
# def compute_uv(cog, chunk):
    # def compute_uv_from_unitcube(x, y, z, face):
        # """Compute UV coords from intersection point and face.

        # The cube is unfold this way:

              # +Z
        # +X +Y -X -Y
              # -Z

        # """
        # cx, cy, cz = cog
        # pt0, pt1, pt2 = (x - cx) / 1000, (y - cy) / 1000, (z - cz) / 1000
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
        # return res

    # return [compute_uv_from_unitcube(x, y, z, face) for x, y, z, face in chunk]


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

    def compute_uv_from_unitcube(color, point):
        """Compute UV coords from intersection point and face.

        The cube is unfold this way:

              +Z
        +X +Y -X -Y
              -Z

        """
        pt0, pt1, pt2 = fdiv(sub(point, cog), 1000)

        if color == 0:  # _UnitCubeFaceEnum.XPLUS
            res = (pt1, pt2)
        elif color == 1:  # _UnitCubeFaceEnum.XMINUS
            res = (-pt1, pt2)
        elif color == 2:  # _UnitCubeFaceEnum.YPLUS
            res = (-pt0, pt2)
        elif color == 3:  # _UnitCubeFaceEnum.YMINUS
            res = (pt0, pt2)
        elif color == 4:  # _UnitCubeFaceEnum.ZPLUS
            res = (pt0, pt1)
        elif color == 5:  # _UnitCubeFaceEnum.ZMINUS
            res = (pt0, -pt1)
        return res

    # Inputs
    cog, color, triangles = chunk

    # Compute points and facets
    points = set(chain.from_iterable(triangles))
    points = {p: i for i, p in enumerate(points)}
    facets = [(points[p1], points[p2], points[p3]) for p1, p2, p3 in triangles]
    points = list(points.keys())

    # Compute uvs
    # TODO could precalculate compute_uv!
    uv = [compute_uv_from_unitcube(color, point) for point in points]

    return points, facets, uv


# *************************************************************************************


def add(*vectors):
    return tuple(sum(x) for x in zip(*vectors))


def sub(vec1, vec2):
    return tuple(map(op_sub, vec1, vec2))


def fmul(vec, flt):
    return tuple(x * flt for x in vec)


def fdiv(vec, flt):
    return tuple(x / flt for x in vec)


def barycenter(facet):
    return fdiv(add(*facet), len(facet))


def length(vec):
    return sqrt(sum(x**2 for x in vec))


def normal(triangle):
    # (p1 - p0) ^ (p2 - p0)
    point0, point1, point2 = triangle
    vec1 = sub(point1, point0)
    vec2 = sub(point2, point0)
    normal = (
        vec1[1] * vec2[2] - vec1[2] * vec2[1],
        vec1[2] * vec2[0] - vec1[0] * vec2[2],
        vec1[0] * vec2[1] - vec1[1] * vec2[0],
    )
    return normal

def dot(vec1, vec2):
    """Dot product."""
    return sum(map(op_mul, vec1, vec2))

def transform(matrix, vec):
    """Transform a 3D vector with a transformation matrix 4x4."""
    vec2 = (*vec, 1)
    return tuple(dot(line, vec2) for line in matrix[:-1])


# *************************************************************************************


def main(points, facets, transmat):
    """Entry point for __main__.

    This code executes in main process.
    Keeping this code out of global scope makes all local objects to be freed
    at the end of the function and thus avoid memory leaks.
    """
    import multiprocessing as mp
    import os
    import shutil
    import itertools

    # Only >= 3.8
    def batched(iterable, n):
        "Batch data into lists of length n. The last batch may be shorter."
        # batched('ABCDEFG', 3) --> ABC DEF G
        # from Python itertools documentation...
        it = iter(iterable)
        while batch := list(islice(it, n)):
            yield batch

    # Set working directory
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set executable
    executable = shutil.which("pythonw")
    if not executable:
        executable = shutil.which("python")
        if not executable:
            raise RuntimeError("No Python executable")
    ctx = mp.get_context("spawn")
    ctx.set_executable(executable)

    CHUNK_SIZE = 20000
    NPROC = max(6, os.cpu_count())  # At least, number of faces

    # TODO Move elsewhere
    def grouper(iterable, n, fillvalue=None):
        "Collect data into fixed-length chunks or blocks"
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return itertools.zip_longest(*args, fillvalue=fillvalue)

    transmat = tuple(grouper(transmat.A, 4))

    # Run
    try:
        with ctx.Pool(NPROC) as pool:
            # Compute colors, and partial sums for center of gravity
            triangles = [tuple(points[i] for i in facet) for facet in facets]
            chunks = batched(triangles, CHUNK_SIZE)
            data = pool.imap(colorize, chunks)

            # Concatenate/reduce processed chunks
            def chunk_reducer(x, y):
                """Reducer for colors chunks."""
                running_colors, running_centroid, running_area_sum = x
                colors, centroid, area_sum = y
                running_centroid = add(running_centroid, centroid)
                running_area_sum += area_sum
                running_colors += colors
                return running_colors, running_centroid, running_area_sum

            init_data = ([], (0.0, 0.0, 0.0), 0.0)
            data = reduce(chunk_reducer, data, init_data)
            triangle_colors, centroid, area_sum = data

            # Compute center of gravity
            cog = fdiv(centroid, area_sum)

            # Generate 6 sublists of monochrome triangles
            # TODO merge with previous computation?
            def triangle_reducer(x, y):
                itriangle, color = y
                x[color].append(triangles[itriangle])
                return x

            init_monochrome_triangles = [[], [], [], [], [], []]
            monochrome_triangles = reduce(
                triangle_reducer,
                enumerate(triangle_colors),
                init_monochrome_triangles,
            )
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
                subfacets = [
                    (index1 + offset, index2 + offset, index3 + offset)
                    for index1, index2, index3 in subfacets
                ]
                facets += subfacets
                uvmap += subuv

            # Transform points (with transmat)
            _transform_points = partial(transform_points, transmat)
            output = pool.imap(_transform_points, batched(points, CHUNK_SIZE))
            points = sum(output, [])

    finally:
        os.chdir(save_dir)

    return points, facets, uvmap


# *************************************************************************************

if __name__ == "__main__":
    # Get variables
    # pylint: disable=used-before-assignment
    try:
        facets
    except NameError:
        facets = []

    try:
        points
    except NameError:
        points = []

    try:
        uvmap
    except NameError:
        uvmap = []

    try:
        transmat
    except NameError:
        transmat = None

    points, facets, uvmap = main(points, facets, transmat)
