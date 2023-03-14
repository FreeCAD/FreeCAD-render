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
    normals = [
        (point_index, *fmul(normal, angle * area))
        for facet, normal, area, angles in it_facets
        for point_index, angle in zip(facet, angles)
    ]
    return normals





# *****************************************************************************


def init(shared):
    """Initialize pool of processes."""
    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    SHARED_POINTS = shared["points"]

    global SHARED_FACETS
    SHARED_FACETS = shared["facets"]

    global SHARED_NORMALS
    SHARED_NORMALS = shared["normals"]

    global SHARED_AREAS
    SHARED_AREAS = shared["areas"]


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
    import itertools
    import time
    import struct

    tm0 = time.time()
    if showtime:
        msg = (
            f"start vnormal computation: {len(points)} points, "
            f"{len(facets)} facets"
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
        shared = {
            "points": ctx.RawArray("f", SharedWrapper(points, 3)),
            "facets": ctx.RawArray("l", SharedWrapper(facets, 3)),
            "normals": ctx.RawArray("f", SharedWrapper(normals, 3)),
            "areas": ctx.RawArray("f", areas),
            "wnormals": ctx.RawArray("f", len(facets) * 4 * 3),
            "vnormals": ctx.RawArray("f", len(points) * 3)
        }
        tick("prepare shared")
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")

            # Compute weighted normals (n per vertex)
            chunks = make_chunks(chunk_size, len(facets))
            data = pool.imap_unordered(compute_weighted_normals, chunks)
            tick("weighted normals")

            # Reduce weighted normals (one per vertex)
            vnorms = [(0, 0, 0)] * len(points)
            for chunk in data:
                for point_index, *weighted_vnorm in chunk:
                    vnorms[point_index] =  add(vnorms[point_index], weighted_vnorm)
            tick("reduced weighted normals")

            # Normalize  (TODO)
            vnorms = [safe_normalize(n) for n in vnorms]
            tick("normalize")
    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin
        del shared

    return vnorms

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
        VNORMALS
    except NameError:
        VNORMALS = []

    try:
        SHOWTIME
    except NameError:
        SHOWTIME = False

    VNORMALS = main(
        PYTHON, POINTS, FACETS, NORMALS, AREAS, SHOWTIME
    )
