# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2023 Howetuft <howetuft@gmail.com>                      *
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

"""This script implements vertex normals computation, in multiprocessing."""

import sys
import os
import struct
import gc

try:
    import numpy as np

    USE_NUMPY = True
except ModuleNotFoundError:
    USE_NUMPY = False

sys.path.insert(0, os.path.dirname(__file__))
# pylint: disable=wrong-import-position
from vector3d import (
    fmul,
    angles,
    add,
    safe_normalize,
)

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

def compute_weighted_normals(chunk):
    """Compute weighted normals for each point."""
    start, stop = chunk

    it_facets = (
        (getfacet(i), getnormal(i), getarea(i))
        for i in range(start, stop)
    )

    it_facets = (
        (facet, normal, area, angles(tuple(getpoint(i) for i in facet)))
        for facet, normal, area in it_facets
    )
    normals = b"".join(
        struct.pack("lfff", point_index, *fmul(normal, angle * area))
        for facet, normal, area, angles in it_facets
        for point_index, angle in zip(facet, angles)
    )
    return normals


# *****************************************************************************

def normalize(chunk):
    """Normalize normal vectors"""
    start, stop = chunk

    fmt = "fff"
    f3struct = struct.Struct(fmt)
    f3pack = f3struct.pack
    f3iter_unpack = f3struct.iter_unpack
    f3itemsize = struct.calcsize(fmt)

    vnormals = memoryview(SHARED_VNORMALS).cast("b")[start * f3itemsize: stop * f3itemsize]

    result = b"".join(f3pack(*safe_normalize(v)) for v in f3iter_unpack(vnormals))

    vnormals[::] = memoryview(result).cast("b")


def normalize_np(chunk):

    start, stop = chunk
    vnormals = np.asarray(SHARED_VNORMALS[start*3:stop*3], dtype="f4")
    vnormals = np.reshape(vnormals,[stop-start, 3])

    magnitudes = np.sqrt((vnormals**2).sum(-1))
    magnitudes = np.expand_dims(magnitudes, axis=1)
    vnormals = np.divide(vnormals, magnitudes, where=magnitudes != 0.0)


# *****************************************************************************


def init(shared):
    """Initialize pool of processes."""
    gc.disable()

    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    SHARED_POINTS = shared["points"]

    global SHARED_FACETS
    SHARED_FACETS = shared["facets"]

    global SHARED_NORMALS
    SHARED_NORMALS = shared["normals"]

    global SHARED_AREAS
    SHARED_AREAS = shared["areas"]

    global SHARED_VNORMALS
    SHARED_VNORMALS = shared["vnormals"]

# *****************************************************************************


def main(python, points, facets, normals, areas, showtime, out_vnormals):
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
    import struct

    tm0 = time.time()
    if showtime:
        msg = (
            f"start vnormal computation: {len(points) // 3} points, "
            f"{len(facets) // 3} facets"
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

    def grouper(iterable, number, fillvalue=None, count=None):
        "Collect data into fixed-length chunks or blocks"
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * number
        res = itertools.zip_longest(*args, fillvalue=fillvalue)
        res = itertools.islice(res, count)
        return res

    def run_unordered(pool, function, iterable):
        imap = pool.imap_unordered(function, iterable)
        for _ in imap:
            pass

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
        shared = {
            "points": points,
            "facets": facets,
            "normals": normals,
            "areas": areas,
            "vnormals": out_vnormals,
        }
        tick("prepare shared")
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")

            gc.disable()

            # Compute weighted normals (n per vertex)
            chunks = make_chunks(chunk_size, len(facets) // 3)
            data = pool.imap_unordered(compute_weighted_normals, chunks)

            # Reduce weighted normals (one per vertex)
            vnorms = shared["vnormals"]
            wstruct = struct.Struct("lfff")
            for chunk in data:
                for point_index, *weighted_vnorm in wstruct.iter_unpack(chunk):
                    offset = point_index * 3
                    vnorms[offset] += weighted_vnorm[0]
                    vnorms[offset + 1] += weighted_vnorm[1]
                    vnorms[offset + 2] += weighted_vnorm[2]
            tick("reduced weighted normals")

            # Normalize
            chunks = make_chunks(chunk_size, len(points) // 3)
            run_unordered(pool, normalize_np if USE_NUMPY else normalize, chunks)
            tick("normalize")

            # Write output buffer
            # out_vnormals[::] = shared["vnormals"]
            tick("write buffer")

    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin
        gc.enable()


# *****************************************************************************

if __name__ == "__main__":
    main(PYTHON, POINTS, FACETS, NORMALS, AREAS, SHOWTIME, OUT_VNORMALS)

    # Clean (remove references to foreign objects)
    PYTHON = None
    POINTS = None
    FACETS = None
    NORMALS = None
    AREAS = None
    SHOWTIME = None
    OUT_VNORMALS = None
