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

"""Script for adjacency lists computation in multiprocessing mode."""

import sys
import os
import functools
import itertools
import operator
import time
import struct
import gc
import collections
from math import radians, cos

sys.path.insert(0, os.path.dirname(__file__))
# pylint: disable=wrong-import-position
import vector3d


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


# *****************************************************************************


def compute_adjacents(chunk):
    """Compute adjacency lists for a chunk of facets."""
    # Init
    start, stop = chunk
    count_facets = len(SHARED_FACETS) // 3
    count_points = len(SHARED_POINTS) // 3

    split_angle = radians(30)  # TODO
    split_angle_cos = cos(split_angle)
    dot = vector3d.dot

    l3struct = struct.Struct("lll")
    l3size = l3struct.size
    l3unpack_from = l3struct.unpack_from

    global FACETS_PER_POINT
    if FACETS_PER_POINT is None:
        # For each point, compute facets that contain this point as a vertex
        FACETS_PER_POINT = [[] for _ in range(count_points)]
        l3struct = struct.Struct("lll")
        l3size = l3struct.size
        l3unpack_from = l3struct.unpack_from

        iterator = (
            (FACETS_PER_POINT[point_index], facet_index)
            for facet_index in range(count_facets)
            for point_index in l3unpack_from(
                SHARED_FACETS, facet_index * l3size
            )
        )

        append = list.append
        any(
            itertools.starmap(append, iterator)
        )  # Sorry, we use side effect (faster)...

    @functools.lru_cache(stop - start)
    def getfacet_as_set(ifacet):
        return set(l3unpack_from(SHARED_FACETS, ifacet * l3size))

    # Compute adjacency for the chunk
    # Warning: facet_idx in [0, stop - start], other_idx in [0, count_facets]
    chain = itertools.chain.from_iterable
    iterator = (
        (adjacents[facet_idx], other_idx)
        for facet_idx, facet in enumerate(
            map(getfacet_as_set, range(start, stop))
        )
        for other_idx in chain(FACETS_PER_POINT[p] for p in facet)
        if len(facet & getfacet_as_set(other_idx)) == 2
        and dot(getnormal(facet_idx + start), getnormal(other_idx))
        >= split_angle_cos
    )

    adjacents = [set() for _ in range(stop - start)]

    add = set.add
    any(
        itertools.starmap(add, iterator)
    )  # Sorry, we use side effect (faster)...

    SHARED_ADJACENCY[start * 3 : stop * 3] = [
        a
        for adj in adjacents
        for a, _ in itertools.zip_longest(adj, range(3), fillvalue=-1)
    ]


# *****************************************************************************


def _connected_facets(
    starting_facet_index,
    adjacents,
    tags,
    new_tag,
):
    """Get the maximal connected component containing the starting facet.

    It uses a depth-first search algorithm, iterative version.
    Caveat:
    - tags may be modified by the algorithm.

    Args:
        starting_facet_index -- the index of the facet to start
            with (integer)
        adjacents -- adjacency lists (one list per facet)
        tags -- the tags that have already been set (list, same size as
            self.__facets)
        new_tag -- the tag to use to mark the component

    Returns:
        A list of tags (same size as self.__facets). The elements tagged
        with 'new_tag' are the computed connected component.
    """
    # Create and init stack
    stack = [starting_facet_index]

    # Tag starting facet
    tags[starting_facet_index] = new_tag

    while stack:
        # Current index (stack top)
        current_index = stack[-1]

        # Forward
        while adjacents[current_index]:
            successor_index = adjacents[current_index].pop()

            if tags[successor_index] is None:
                # successor is not tagged, we can go on forward
                tags[successor_index] = new_tag
                stack.append(successor_index)
                current_index = successor_index

        # Backward
        successor_index = stack.pop()

    # Final
    return tags


def connected_components(chunk):
    """Get all connected components of facets in the mesh."""
    start, stop = chunk

    l3struct = struct.Struct("lll")
    l3size = l3struct.size
    l3unpack_from = l3struct.unpack_from

    adjacents = [
        [
            f - start
            for f in l3unpack_from(SHARED_ADJACENCY, ifacet * l3size)
            if start <= f < stop
        ]
        for ifacet in range(start, stop)
    ]

    tags = [None] * (stop - start)
    tag = None

    iterator = zip(
        itertools.count(start), (x for x, y in enumerate(tags) if y is None)
    )
    for tag, starting_point in iterator:
        tags = _connected_facets(
            starting_point,
            adjacents,
            tags,
            tag,
        )

    SHARED_TAGS[start:stop] = tags

    # TODO
    # Reset unnecessary adj
    # for i in range(start,stop):
    # if start <= SHARED_ADJACENCY[i] < stop:
    # SHARED_ADJACENCY[i] = -1
    # print("tag ", tag - start)  # Debug


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

    global FACETS_PER_POINT
    FACETS_PER_POINT = None

    global SHARED_ADJACENCY
    SHARED_ADJACENCY = shared["adjacency"]

    global SHARED_TAGS
    SHARED_TAGS = shared["tags"]


# *****************************************************************************


def main(python, points, facets, normals, areas, showtime, out_adjacents):
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
            f"start adjacency computation: {len(points)} points, "
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
            # max 3 adjacents/facet
            "adjacency": ctx.RawArray("l", len(facets) * 3),
            "tags": ctx.RawArray("l", len(facets)),
        }
        tick("prepare shared")
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")

            # Compute adjacency
            chunks = make_chunks(chunk_size, len(facets))
            run_unordered(pool, compute_adjacents, chunks)

            tick("adjacency")

            # Update output buffer
            out_adjacents[::] = shared["adjacency"]

            tick("output buffer")

            # Compute connected components
            chunks = make_chunks(len(facets) // nproc, len(facets))
            run_unordered(pool, connected_components, chunks)

            tick("connected components (map)")

            # TODO Isolate in a function
            subcomponents = collections.defaultdict(list)
            subadjacency = collections.defaultdict(list)
            tags = shared["tags"]
            adjacency = shared["adjacency"]

            l3struct = struct.Struct("lll")
            l3size = l3struct.size
            l3unpack_from = l3struct.unpack_from

            iterator = (
                (
                    subcomponents[tag],
                    ifacet,
                    subadjacency[tag],
                    [
                        tags[ifacet2]
                        for ifacet2 in l3unpack_from(
                            adjacency, ifacet * l3size
                        )
                        if ifacet2 >= 0
                    ],
                )
                for ifacet, tag in enumerate(tags)
            )

            for subcomp, ifacet, subadj, subtags in iterator:
                subcomp.append(ifacet)
                subadj.extend(subtags)

            tick("connected components (reduce)")
            print(
                f"{len(subcomponents)} subcomponents, {len(subadjacency)} adjacent lists"
            )

    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin


# *****************************************************************************

if __name__ == "__main__":
    main(PYTHON, POINTS, FACETS, NORMALS, AREAS, SHOWTIME, OUT_ADJACENTS)

    # Clean (remove references to foreign objects)
    PYTHON = None
    POINTS = None
    FACETS = None
    NORMALS = None
    AREAS = None
    SHOWTIME = None
    OUT_ADJACENTS = None
