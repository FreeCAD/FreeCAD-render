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
import multiprocessing as mp
import functools
import math


def compute_submeshes(facets):
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
    centers = ((barycenter(facet), normal(facet)) for facet in facets)
    # areas_centers = ((barycenter, 0.5 * length(normal)) for normal, barycenter in normals_centers)

    def reducer(x,y):
        centroid, area_sum, face_colors = x
        barycenter, normal = y

        area = 0.5 * length(normal)

        centroid = add(centroid, fmul(barycenter, area))
        area_sum += area
        face_colors.append(intersect_unitcube_face(normal))

        return centroid, area_sum, face_colors

    init_reducer = ((0.0, 0.0, 0.0), 0.0, [])
    result = functools.reduce(reducer, centers, init_reducer)
    return result  # centroid, area sum, face colors


def compute_uv(cog, chunk):
    def compute_uv_from_unitcube(x, y, z, face):
        """Compute UV coords from intersection point and face.

        The cube is unfold this way:

              +Z
        +X +Y -X -Y
              -Z

        """
        cx, cy, cz = cog
        pt0, pt1, pt2 = (x - cx) / 1000, (y - cy) / 1000, (z - cz) / 1000
        if face == 0:  # _UnitCubeFaceEnum.XPLUS
            res = (pt1, pt2)
        elif face == 1:  # _UnitCubeFaceEnum.XMINUS
            res = (-pt1, pt2)
        elif face == 2:  # _UnitCubeFaceEnum.YPLUS
            res = (-pt0, pt2)
        elif face == 3:  # _UnitCubeFaceEnum.YMINUS
            res = (pt0, pt2)
        elif face == 4:  # _UnitCubeFaceEnum.ZPLUS
            res = (pt0, pt1)
        elif face == 5:  # _UnitCubeFaceEnum.ZMINUS
            res = (pt0, -pt1)
        return res


    return [compute_uv_from_unitcube(x, y, z, face) for x, y, z, face in chunk]

def add(*vectors):
    return tuple(sum(x) for x in zip(*vectors))

def sub(vec1, vec2):
    return tuple(x - y for x, y in zip(vec1, vec2))

def fmul(vec, flt):
    return tuple(x * flt for x in vec)

def fdiv(vec, flt):
    return tuple(x / flt for x in vec)

def barycenter(facet):
    return fdiv(add(*facet), len(facet))

def length(vec):
    return math.sqrt(sum(x ** 2 for x in vec))

def normal(facet):
    # (p1 - p0) ^ (p2 - p0)
    pt0, pt1, pt2 = facet
    vec1 = sub(pt1, pt0)
    vec2 = sub(pt2, pt0)
    normal = (
        vec1[1] * vec2[2] - vec1[2] * vec2[1],
        vec1[2] * vec2[0] - vec1[0] * vec2[2],
        vec1[0] * vec2[1] - vec1[1] * vec2[0],
    )
    return normal

if __name__ == "__main__":
    import os
    import shutil
    import itertools
    import functools

    import Mesh

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
        transmat
    except NameError:
        transmat = None

    # Only >= 3.8
    def batched(iterable, n):
        "Batch data into lists of length n. The last batch may be shorter."
        # batched('ABCDEFG', 3) --> ABC DEF G
        # from Python itertools documentation...
        it = iter(iterable)
        while batch := list(itertools.islice(it, n)):
            yield batch

    # Set directory and stdout
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
    NPROC = os.cpu_count()

    # Run
    try:
        point_facets = [tuple(points[i] for i in facet) for facet in facets]
        chunks = batched(point_facets, CHUNK_SIZE)
        with ctx.Pool(NPROC) as pool:
            # Compute submeshes
            data = pool.imap(compute_submeshes, chunks)

            # Concatenate data
            def chunk_reducer(x, y):
                running_centroid, running_area_sum, running_colors = x
                centroid, area_sum, colors = y

                running_centroid = add(running_centroid, centroid)
                running_area_sum += area_sum
                running_colors += colors

                return running_centroid, running_area_sum, running_colors

            init_data = ((0.0, 0.0, 0.0), 0.0, [])
            data = functools.reduce(chunk_reducer, data, init_data)

            centroid, area_sum, colors = data

            faces = enumerate(colors)
            cog = fdiv(centroid, area_sum)

            def face_reducer(x, y):
                iface, face = y
                x[face].append(point_facets[iface])
                return x
            init_face_facets = [[], [], [], [], [], []]
            face_facets = functools.reduce(
                face_reducer, faces, init_face_facets
            )

            # Compute final mesh and uvmap
            mesh = Mesh.Mesh()
            uv_results = []
            for cubeface, facets in enumerate(face_facets):
                submesh = Mesh.Mesh(facets)
                points = submesh.Points
                data = ((p.x, p.y, p.z, cubeface) for p in points)
                chunks = batched(data, CHUNK_SIZE)
                compute = functools.partial(compute_uv, cog)
                uv_results.append(pool.map_async(compute, chunks))
                submesh.transform(transmat)
                mesh.addMesh(submesh)
                del submesh

            uvmap = [
                uv
                for mapres in uv_results
                for chunks in mapres.get()
                for uv in chunks
            ]

            # Clean
            del facets
            del face_facets
            del data
    finally:
        os.chdir(save_dir)
