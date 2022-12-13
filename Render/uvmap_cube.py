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

def _intersect_unitcube_face(arg):
    """Get the face of the unit cube intersected by a line from origin.

    Args:
        direction -- The directing vector for the intersection line
        (a 3-float sequence)

    Returns:
        A face from the unit cube (_UnitCubeFaceEnum)
    """
    points, direction = arg
    dirx, diry, dirz = direction
    dabsx, dabsy, dabsz = abs(dirx), abs(diry), abs(dirz)

    if dabsx >= dabsy and dabsx >= dabsz:
        return (
            (points, 0)  # _UnitCubeFaceEnum.XPLUS
            if dirx >= 0
            else (points, 1)  # _UnitCubeFaceEnum.XMINUS
        )

    if dabsy >= dabsx and dabsy >= dabsz:
        return (
            (points, 2)  # _UnitCubeFaceEnum.YPLUS
            if diry >= 0
            else (points, 3)  # _UnitCubeFaceEnum.YMINUS
        )

    return (
        (points, 4)  # _UnitCubeFaceEnum.ZPLUS
        if dirz >= 0
        else (points, 5)  # _UnitCubeFaceEnum.ZMINUS
    )



if __name__ == "__main__":
    import os
    import shutil
    import operator
    import itertools
    import time

    global facets

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
        facet_normals = ((f.Points, tuple(f.Normal)) for f in facets)
        # TODO: divide into chunks and run a process on chunk. No map
        print("iterator", time.time() - tm0)
        with mp.Pool(NPROC) as pool:
            data = pool.imap_unordered(_intersect_unitcube_face, facet_normals, CHUNK_SIZE)
            print("imap", time.time() - tm0)
            l = list(data)
            print("list", time.time() - tm0)
            it1 = operator.itemgetter(1)
            sorted(data, key=it1)
            print("sort", time.time() - tm0)
            face_facets = ([], [], [], [], [], [])
            for facet, index in data:
                face_facets[index].append(facet)
            print("loop", time.time() - tm0)
    finally:
        os.chdir(save_dir)
