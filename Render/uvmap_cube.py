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




def compute_submeshes(normals):
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

    return [intersect_unitcube_face(n) for n in normals]

def compute_uv_from_unitcube(x, y, z, face):
    """Compute UV coords from intersection point and face.

    The cube is unfold this way:

          +Z
    +X +Y -X -Y
          -Z

    """
    cx, cy, cz = COG
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


def compute_uv(chunk):
    return [compute_uv_from_unitcube(x, y, z, face) for x, y, z, face in chunk]

def init(*args):
    global COG
    COG, *_ = args

if __name__ == "__main__":
    import os
    import shutil
    import operator
    import itertools
    import time
    import functools

    import Mesh

    # Get variables
    # pylint: disable=used-before-assignment
    try:
        facets
    except NameError:
        facets = []

    try:
        cog
    except NameError:
        cog = (0.0, 0.0, 0.0)

    try:
        transmat
    except NameError:
        transmat = None

    # TODO Only >= 3.8
    def batched(iterable, n):
        "Batch data into lists of length n. The last batch may be shorter."
        # batched('ABCDEFG', 3) --> ABC DEF G
        # from Python itertools documentation...
        if n < 1:
            raise ValueError("n must be at least one")
        it = iter(iterable)
        while batch := list(itertools.islice(it, n)):
            yield batch

    # Set directory and stdout
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set executable
    executable = shutil.which("python")
    if not executable:
        raise RuntimeError("No Python executable")
    ctx = mp.get_context("spawn")
    ctx.set_executable(executable)

    CHUNK_SIZE = 20000
    NPROC = os.cpu_count()

    # Run
    try:
        tm0 = time.time()
        chunks = batched((tuple(f.Normal) for f in facets), CHUNK_SIZE)
        with ctx.Pool(NPROC, init, (cog,)) as pool:
            # Compute submeshes
            data = pool.imap(compute_submeshes, chunks)
            faces = (
                (ichunk * CHUNK_SIZE + iface, face)
                for ichunk, chunk in enumerate(data)
                for iface, face in enumerate(chunk)
            )

            def face_reducer(x, y):
                iface, face = y
                x[face].append(facets[iface])
                return x
            face_facets = functools.reduce(face_reducer, faces, [[], [], [], [], [], []])
            print("face_facets", time.time() - tm0)

            # Compute final mesh and uvmap
            mesh = Mesh.Mesh()
            uv_results = []
            for cubeface, facets in enumerate(face_facets):
                submesh = Mesh.Mesh(facets)
                points = submesh.Points
                data = ((p.x, p.y, p.z, cubeface) for p in points)
                chunks = batched(data, CHUNK_SIZE)
                uv_results.append(pool.map_async(compute_uv, chunks))
                submesh.transform(transmat)
                mesh.addMesh(submesh)
            print("uvresult", time.time() - tm0)
            uvmap = [uv for mapres in uv_results for chunks in mapres.get() for uv in chunks]
            print("uvmap", time.time() - tm0)

            # Clean
            del face_facets
            del data
    finally:
        os.chdir(save_dir)
