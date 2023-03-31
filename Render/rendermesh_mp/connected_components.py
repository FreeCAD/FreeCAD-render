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


@functools.lru_cache(20000)
def getnormal(idx):
    """Get a normal from its index in the shared memory."""
    idx *= 3
    return (
        SHARED_NORMALS[idx],
        SHARED_NORMALS[idx + 1],
        SHARED_NORMALS[idx + 2],
    )


# *****************************************************************************

# TODO
import cProfile
import pstats
import io
from pstats import SortKey


def compute_adjacents(chunk):
    """Compute adjacency lists for a chunk of facets."""
    # # TODO
    # prof = cProfile.Profile()
    # prof.enable()
    # Init
    start, stop = chunk
    count_facets = len(SHARED_FACETS) // 3
    count_points = len(SHARED_POINTS) // 3

    split_angle = SHARED_SPLIT_ANGLE.value
    split_angle_cos = cos(split_angle)
    dot = vector3d.dot

    l3struct = struct.Struct("lll")
    l3size = l3struct.size
    l3unpack_from = l3struct.unpack_from
    l3iter_unpack = l3struct.iter_unpack

    global FACETS_AS_SETS
    if FACETS_AS_SETS is None:
        FACETS_AS_SETS = [set(facet) for facet in l3iter_unpack(SHARED_FACETS)]

    global FACETS_PER_POINT
    if FACETS_PER_POINT is None:
        # For each point, compute facets that contain this point as a vertex
        FACETS_PER_POINT = [[] for _ in range(count_points)]

        iterator = (
            (FACETS_PER_POINT[point_index], facet_index)
            for facet_index, facet in enumerate(l3iter_unpack(SHARED_FACETS))
            for point_index in facet
        )

        append = list.append
        any(
            itertools.starmap(append, iterator)
        )  # Sorry, we use side effect (faster)...

    # Compute adjacency for the chunk
    # Warning: facet_idx in [0, stop - start], other_idx in [0, count_facets]
    chain = itertools.chain.from_iterable
    iterator = (
        (adjacents[facet_idx], other_idx)
        for facet_idx, facet in enumerate(FACETS_AS_SETS[start:stop])
        for other_idx in set(chain(FACETS_PER_POINT[p] for p in facet))
        if len(facet & FACETS_AS_SETS[other_idx]) == 2
        and dot(getnormal(facet_idx + start), getnormal(other_idx))
        >= split_angle_cos
    )

    adjacents = [[] for _ in range(stop - start)]

    add = list.append
    any(
        itertools.starmap(add, iterator)
    )  # Sorry, we use side effect (faster)...

    SHARED_ADJACENCY[start * 3 : stop * 3] = [
        a
        for adj in adjacents
        for a in itertools.islice(
            itertools.chain(set(adj), (-1, -1, -1)), 0, 3
        )
    ]

    # # TODO
    # prof.disable()
    # sec = io.StringIO()
    # sortby = SortKey.CUMULATIVE
    # pstat = pstats.Stats(prof, stream=sec).sort_stats(sortby)
    # pstat.print_stats()
    # lines = sec.getvalue().splitlines()
    # print("\n".join(lines[:20]))


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


def connected_components(adjacents, offset=0, shared=None):
    tags = [None] * len(adjacents)
    tag = None

    iterator = (x for x, y in enumerate(tags) if y is None)
    shared_current_tag = (
        shared["current_tag"] if shared else SHARED_CURRENT_TAG
    )

    for starting_point in iterator:
        with shared_current_tag:
            tag = shared_current_tag.value
            shared_current_tag.value += 1

        tags = _connected_facets(
            starting_point,
            adjacents,
            tags,
            tag,
        )
    return tags


def connected_components_chunk(chunk):
    """Get all connected components of facets in a submesh."""
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

    tags = connected_components(adjacents, offset=start)

    # Write tags buffer
    SHARED_TAGS[start:stop] = list(tags)

    # Write adjacency buffer
    adjacents2 = {
        (SHARED_TAGS[ifacet], f)
        for ifacet in range(start, stop)
        for f in l3unpack_from(SHARED_ADJACENCY, ifacet * l3size)
        if 0 <= f < start or f > stop
    }
    adjacents2 = list(itertools.chain.from_iterable(adjacents2))

    shared_current_adj = SHARED_CURRENT_ADJ
    with shared_current_adj:
        offset = shared_current_adj.value
        shared_current_adj.value += len(adjacents2)

    SHARED_ADJACENCY2[offset : offset + len(adjacents2)] = adjacents2


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

    global SHARED_SPLIT_ANGLE
    SHARED_SPLIT_ANGLE = shared["split_angle"]

    global FACETS_PER_POINT
    FACETS_PER_POINT = None

    global FACETS_AS_SETS
    FACETS_AS_SETS = None

    global SHARED_ADJACENCY
    SHARED_ADJACENCY = shared["adjacency"]

    global SHARED_ADJACENCY2
    SHARED_ADJACENCY2 = shared["adjacency2"]

    global SHARED_TAGS
    SHARED_TAGS = shared["tags"]

    global SHARED_CURRENT_TAG
    SHARED_CURRENT_TAG = shared["current_tag"]

    global SHARED_CURRENT_ADJ
    SHARED_CURRENT_ADJ = shared["current_adj"]


# *****************************************************************************


def main(
    python, points, facets, normals, areas, split_angle, showtime, out_tags
):
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
            "adjacency2": ctx.RawArray("l", len(facets) * 2 * 3),  # 2nd pass
            "tags": ctx.RawArray("l", len(facets)),
            "split_angle": ctx.RawValue("f", split_angle),
            "current_tag": ctx.Value("l", 0),
            "current_adj": ctx.Value("l", 0),
        }
        tick("prepare shared")
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")

            # Compute adjacency
            chunks = make_chunks(chunk_size, len(facets))
            run_unordered(pool, compute_adjacents, chunks)

            tick("adjacency")

            # Compute connected components
            chunks = make_chunks(len(facets) // nproc, len(facets))
            run_unordered(pool, connected_components_chunk, chunks)

            tick("connected components (pass #1 - map)")

            # Update subcomponents
            tags = shared["tags"]
            adjacency = shared["adjacency"]

            maxtag = shared["current_tag"].value
            subcomponents = [[] for i in range(maxtag)]
            subadjacency = [[] for i in range(maxtag)]

            for ifacet, tag in enumerate(tags):
                subcomponents[tag].append(ifacet)

            # Update adjacents
            l2struct = struct.Struct("ll")
            l2size = l2struct.size
            l2unpack_from = l2struct.unpack_from

            iterator = itertools.takewhile(
                lambda x: x != (0, 0),
                l2struct.iter_unpack(shared["adjacency2"]),
            )
            iterator = ((tag, tags[ifacet]) for tag, ifacet in iterator)
            iterator = (
                (tag, other_tag)
                for tag, other_tag in iterator
                if tag != other_tag
            )
            for tag, other_tag in iterator:
                subadjacency[tag].append(other_tag)

            tick("connected components (pass #1 - reduce)")

            final_tags = connected_components(subadjacency, shared=shared)
            tick("connected components (pass #2 - map)")

            # Update and write tags
            for i in range(len(tags)):
                tags[i] = final_tags[tags[i]]

            tick("connected components (pass #2 - reduce)")

            # Write output buffer
            out_tags_view = memoryview(out_tags).cast("l")
            out_tags_view[::] = memoryview(tags).cast("b").cast("l")

            tick("connected components - write outputs")

    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin


# *****************************************************************************

if __name__ == "__main__":
    main(
        PYTHON, POINTS, FACETS, NORMALS, AREAS, SPLIT_ANGLE, SHOWTIME, OUT_TAGS
    )

    # Clean (remove references to foreign objects)
    PYTHON = None
    POINTS = None
    FACETS = None
    NORMALS = None
    AREAS = None
    SPLIT_ANGLE = None
    SHOWTIME = None
    OUT_TAGS = None
