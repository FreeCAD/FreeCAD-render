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
import time

def _intersect_unitcube_face(direction):
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

def normal(facet):
    a, b, c = facet
    v = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    res = (
        v[1] * w[2] - v[2] * w[1],
        v[2] * w[0] - v[0] * w[2],
        v[0] * w[1] - v[1] * w[0],
    )
    return res


def isolate_submeshes(facets):
    submeshes = ([], [], [], [], [], [])
    for facet in facets:
        cubeface = _intersect_unitcube_face(normal(facet))
        # Add facet to corresponding submesh
        submeshes[cubeface].append(facet)
    return submeshes

if __name__ == "__main__":
    import os
    import shutil
    import operator
    import itertools

    global facets

    def batched(iterable, n):
        "Batch data into lists of length n. The last batch may be shorter."
        # batched('ABCDEFG', 3) --> ABC DEF G
        # from Python itertools documentation...
        if n < 1:
            raise ValueError("n must be at least one")
        it = iter(iterable)
        while (batch := list(itertools.islice(it, n))):
            yield batch


    # Set directory and stdout
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set executable
    executable = shutil.which("python")
    if not executable:
        raise RuntimeError("No Python executable")
    mp.set_executable(executable)
    mp.set_start_method("spawn", force=True)

    CHUNK_SIZE = 20000
    NPROC = os.cpu_count()


    # Run
    try:
        tm0 = time.time()
        chunks = batched((f.Points for f in facets), CHUNK_SIZE)
        print("iterator", time.time() - tm0)
        with mp.Pool(NPROC) as pool:
            data = pool.map(isolate_submeshes, chunks)
            print("map", time.time() - tm0)
            face_facets = [[], [], [], [], [], []]
            for subm in data:
                face_facets[0] += subm[0]
                face_facets[1] += subm[1]
                face_facets[2] += subm[2]
                face_facets[3] += subm[3]
                face_facets[4] += subm[4]
                face_facets[5] += subm[5]
            print("loop", time.time() - tm0)

            # it1 = operator.itemgetter(1)
            # sorted(data, key=it1)
            # print("sort", time.time() - tm0)
            # face_facets = ([], [], [], [], [], [])
            # for facet, index in data:
                # face_facets[index].append(facet)
            # print("loop", time.time() - tm0)
    finally:
        os.chdir(save_dir)
