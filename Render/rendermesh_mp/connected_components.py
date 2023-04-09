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
from math import cos, hypot, isclose

try:
    import numpy as np

    USE_NUMPY = True
except ModuleNotFoundError:
    USE_NUMPY = False

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

    global FACETS_PER_POINT
    global UNPACKED_FACETS
    if FACETS_PER_POINT is None:
        UNPACKED_FACETS = list(l3iter_unpack(SHARED_FACETS))
        # For each point, compute facets that contain this point as a vertex
        FACETS_PER_POINT = [[] for _ in range(count_points)]

        iterator = (
            (FACETS_PER_POINT[point_index], facet_index)
            for facet_index, facet in enumerate(UNPACKED_FACETS)
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
        for facet_idx, facet in enumerate(UNPACKED_FACETS[start:stop])
        for other_idx in set(chain(FACETS_PER_POINT[p] for p in facet))
        if len(set(facet) & set(UNPACKED_FACETS[other_idx])) == 2
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

def compute_adjacents_np(chunk):
    """Compute adjacency lists for a chunk of facets.

    Numpy version"""
    start, stop = chunk
    count_facets = len(SHARED_FACETS) // 3
    count_points = len(SHARED_POINTS) // 3

    split_angle = SHARED_SPLIT_ANGLE.value
    split_angle_cos = cos(split_angle)

    # Prepare globals
    global NP_READY
    if not NP_READY:
        print("initialize np")
        facets = np.array(SHARED_FACETS)
        facets.shape = [count_facets, 3]
        facets.sort(axis=1)

        indices = np.arange(len(facets))
        indices = np.tile(indices, 3)

        global EDGES1, EDGES2, EDGES3
        EDGES1 = np.rec.fromarrays((facets[..., 0], facets[..., 1]))
        EDGES2 = np.rec.fromarrays((facets[..., 0], facets[..., 2]))
        EDGES3 = np.rec.fromarrays((facets[..., 1], facets[..., 2]))
        edges = np.concatenate((EDGES1, EDGES2, EDGES3))
        print(f"{len(edges)} total edges")

        global SORTED_FACET_INDICES
        shared_edges = np.array(SHARED_EDGES_NP)
        shared_edges.shape = [count_facets * 3, 3]
        sorted_edges, argsort_edges = np.hsplit(shared_edges, np.array([2,]))
        sorted_edges.dtype = np.dtype([("x", np.int64), ("y", np.int64)])
        sorted_edges = sorted_edges.squeeze()
        argsort_edges = argsort_edges.squeeze()

        SORTED_FACET_INDICES = indices[argsort_edges]

        # Searches
        global UNIQUE_EDGES, UNIQUE_INDICES, UNIQUE_COUNTS
        UNIQUE_EDGES, UNIQUE_INDICES, UNIQUE_COUNTS = np.unique(
            sorted_edges, return_index=True, return_counts=True
        )
        print(f"end initialize np - {len(UNIQUE_EDGES)} unique edges")

        NP_READY = True

    # Work on chunk
    indices_chunk = np.arange(start, stop)
    indices_chunk = np.tile(indices_chunk, 3)
    edges_chunk = np.concatenate((
        EDGES1[start:stop], EDGES2[start:stop], EDGES3[start:stop]
    ))

    unique_indices_left = np.searchsorted(UNIQUE_EDGES, edges_chunk, side="left")
    indices_left = UNIQUE_INDICES[unique_indices_left]
    indices_count = UNIQUE_COUNTS[unique_indices_left]
    indices_right = indices_left + indices_count - 1
    maxindices = np.max(indices_count)
    if not maxindices <= 2:  # We assume only 2 neighbours per edge
        msg = (
            "Warning - More than 2 neighbours per edge "
            f"(found {maxindices})"
            " - Truncation may occur"
        )
        print(msg)
    indices_left = SORTED_FACET_INDICES[indices_left]
    indices_right = SORTED_FACET_INDICES[indices_right]

    pairs_left = np.rec.fromarrays((indices_chunk, indices_left), names="x,y")
    condition_left = np.not_equal(pairs_left.x, pairs_left.y)
    pairs_left = np.compress(condition_left, pairs_left)

    pairs_right = np.rec.fromarrays((indices_chunk, indices_right), names="x,y")
    condition_right = np.not_equal(pairs_right.x, pairs_right.y)
    pairs_right = np.compress(condition_right, pairs_right)

    # Concatenate
    pairs = np.concatenate((pairs_left, pairs_right))

    # Filter with angle
    normals = np.array(SHARED_NORMALS)  # We assume normalized normals
    normals.shape = [count_facets, 3]
    x_normals, y_normals = normals[pairs["x"]], normals[pairs["y"]]
    dotprod = np.einsum("ij,ij->i", x_normals, y_normals)
    condition_angle = dotprod >= split_angle_cos
    pairs = np.compress(condition_angle, pairs)

    # Write buffer
    adjacents = [list() for _ in range(stop - start)]
    for x, y in pairs:
        adjacents[x - start].append(y)

    SHARED_ADJACENCY[start * 3 : stop * 3] = [
        a
        for adj in adjacents
        for a in itertools.islice(
            itertools.chain(set(adj), (-1, -1, -1)), 0, 3
        )
    ]

# *****************************************************************************

def sort_edges_np(chunk):
    # TODO Docstring
    # TODO do edge calculation once
    start, stop = chunk
    count_facets = len(SHARED_FACETS) // 3
    facets = np.array(SHARED_FACETS)
    facets.shape = [count_facets, 3]
    facets.sort(axis=1)

    indices = np.arange(len(facets))

    edges1 = np.rec.fromarrays((facets[..., 0], facets[..., 1], indices))
    edges2 = np.rec.fromarrays((facets[..., 0], facets[..., 2], indices + len(facets)))
    edges3 = np.rec.fromarrays((facets[..., 1], facets[..., 2], indices + 2 * len(facets)))
    edges = np.concatenate((edges1, edges2, edges3))

    return np.sort(edges[start:stop])



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

    global NP_READY
    NP_READY = False

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

    if USE_NUMPY:
        global SHARED_EDGES_NP
        SHARED_EDGES_NP = shared["edges_np"]


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
            "\n"
            f"start adjacency computation: {len(points) // 3} points, "
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

    count_facets = len(facets) // 3

    try:
        shared = {
            "points": points,
            "facets": facets,
            "normals": normals,
            "areas": areas,
            "split_angle": split_angle,
            # max 3 adjacents/facet
            "adjacency": ctx.RawArray("l", count_facets * 3),
            "adjacency2": ctx.RawArray("l", count_facets * 3 * 2),  # 2nd pass
            "tags": out_tags,
            "current_tag": ctx.Value("l", 0),
            "current_adj": ctx.Value("l", 0),
        }
        if USE_NUMPY:  # Numpy only
            shared["edges_np"] = ctx.RawArray("l", count_facets * 3 * 3)
        tick("prepare shared")

        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")

            # Compute adjacency
            if USE_NUMPY:
                def new_merge(a, b):
                    if len(a) < len(b):
                        b, a = a, b
                    c = np.empty(len(a) + len(b), dtype=a.dtype)
                    b_indices = np.arange(len(b)) + np.searchsorted(a, b)
                    a_indices = np.ones(len(c), dtype=bool)
                    a_indices[b_indices] = False
                    c[b_indices] = b
                    c[a_indices] = a
                    return c

                chunks = make_chunks(count_facets * 3 // nproc, count_facets * 3)
                futures = pool.imap_unordered(sort_edges_np, chunks)
                res = None
                for future in futures:
                    if res is None:
                        res = future
                    else:
                        res = new_merge(res, future)
                res.dtype = np.dtype(np.int64)
                shared["edges_np"][:] = list(res.flat)

                tick("prepare edges (np)")

            chunks = make_chunks(chunk_size, count_facets)
            if USE_NUMPY:
                func, tickmsg = compute_adjacents_np, "adjacency (np)"
            else:
                func, tickmsg = compute_adjacents, "adjacency"
            run_unordered(pool, func, chunks)

            tick(tickmsg)

            # Compute connected components
            chunks = make_chunks(count_facets // nproc, count_facets)
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
                out_tags[i] = final_tags[tags[i]]

            tick("connected components (pass #2 - reduce & write)")


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
