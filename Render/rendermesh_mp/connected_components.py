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
import struct
import gc
from math import cos

from itertools import permutations, groupby, starmap


try:
    import numpy as np
    from numpy import bitwise_or, left_shift

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


def compute_adjacents(chunk):
    """Compute adjacency lists for a chunk of facets."""
    start, stop = chunk
    count_points = len(SHARED_POINTS) // 3

    split_angle = SHARED_SPLIT_ANGLE.value
    split_angle_cos = cos(split_angle)
    dot = vector3d.dot

    l3struct = struct.Struct("lll")
    l3iter_unpack = l3struct.iter_unpack

    # pylint: disable=global-variable-undefined
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
    adjacents = [[] for _ in range(stop - start)]
    chain = itertools.chain.from_iterable
    iterator = (
        (adjacents[facet_idx], other_idx)
        for facet_idx, facet in enumerate(UNPACKED_FACETS[start:stop])
        for other_idx in set(chain(FACETS_PER_POINT[p] for p in facet))
        if len(set(facet) & set(UNPACKED_FACETS[other_idx])) == 2
        and dot(getnormal(facet_idx + start), getnormal(other_idx))
        >= split_angle_cos
    )

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


def compute_hashes_np(chunk):
    """Compute hash keys for chunk

    Numpy version
    """
    start, stop = chunk
    hashes = bitwise_or(
        left_shift(ALL_EDGES_LEFT[start:stop], 32),
        ALL_EDGES_RIGHT[start:stop],
    )
    SHARED_HASHES_NP[start:stop] = hashes


itget0 = operator.itemgetter(0)
itget1 = operator.itemgetter(1)


def build_pairs_np(chunk):
    """Build adjacent pairs, numpy-aided."""
    start, stop = chunk

    hashes = np.stack(
        (SHARED_HASHES_NP[start:stop], SHARED_HASHES_INDICES_NP[start:stop]),
        axis=-1,
    )

    # Compute hashtable
    hashtable = (
        permutations(map(itget1, v), 2)
        for v in map(itget1, groupby(hashes, key=itget0))
    )

    # Compute pairs
    pairs = itertools.chain.from_iterable(hashtable)
    pairs = np.fromiter(pairs, dtype=[("x", np.int64), ("y", np.int64)])

    # Build adjacency lists
    facet_pairs = np.stack(
        (INDICES_NP[pairs["x"]], INDICES_NP[pairs["y"]]), axis=-1
    )

    # Filter angle
    split_angle_cos = cos(SHARED_SPLIT_ANGLE.value)
    dotprod = np.einsum(
        "ij,ij->i",
        SHARED_NORMALS_NP[facet_pairs[..., 0]],
        SHARED_NORMALS_NP[facet_pairs[..., 1]],
    )
    facet_pairs = np.compress(dotprod >= split_angle_cos, facet_pairs, axis=0)

    # Write pairs
    with SHARED_CURRENT_PAIR:
        curval = SHARED_CURRENT_PAIR.value

        length = len(facet_pairs)
        pair_slice = SHARED_PAIRS_NP[curval : (curval + length)]

        if len(pair_slice) < len(facet_pairs):
            length = len(pair_slice)
            print("Warning: redundancy in adjacency - truncation", length)
            facet_pairs = facet_pairs[0:length]

        SHARED_PAIRS_NP[curval : curval + length] = facet_pairs
        SHARED_CURRENT_PAIR.value = curval + length


def compute_adjacents_np(chunk):
    """Compute adjacency lists - numpy version."""
    start, stop = chunk

    pairs = SHARED_PAIRS_NP[start:stop]

    # Truncate to 3 adjacents...
    adjacency = (
        (k, (list(map(itget1, v)) + [-1, -1, -1])[0:3])
        for k, v in groupby(pairs, key=itget0)
    )

    any(starmap(set_item_adj, adjacency))


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


def connected_components(adjacents, shared=None):
    """Get all connected components of the submesh delimited by adjacents.

    This function is called both by subprocess (pass #1) and by main process
    (pass #2).

    Returns:
    A list of tags (scalar) corresponding to the graph vertices of adjacency.
    """

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

    tags = connected_components(adjacents)

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
        global SHARED_HASHES_NP
        SHARED_HASHES_NP = np.array(shared["hashes"], copy=False)

        global SHARED_HASHES_INDICES_NP
        SHARED_HASHES_INDICES_NP = np.array(
            shared["hashes_indices"], copy=False
        )

        global SHARED_PAIRS_NP
        SHARED_PAIRS_NP = np.array(shared["pairs"], copy=False)
        SHARED_PAIRS_NP.shape = [-1, 2]

        global SHARED_CURRENT_PAIR
        SHARED_CURRENT_PAIR = shared["current_pair"]

        count_facets = len(SHARED_FACETS) // 3

        facets = np.array(SHARED_FACETS)
        facets.shape = [count_facets, 3]
        facets.sort(axis=1)

        global INDICES_NP
        INDICES_NP = np.arange(len(facets))
        INDICES_NP = np.tile(INDICES_NP, 3)

        global ALL_EDGES_LEFT
        ALL_EDGES_LEFT = np.concatenate(
            (facets[..., 0], facets[..., 0], facets[..., 1])
        )
        global ALL_EDGES_RIGHT
        ALL_EDGES_RIGHT = np.concatenate(
            (facets[..., 1], facets[..., 2], facets[..., 2])
        )

        global SHARED_ADJACENCY_NP
        SHARED_ADJACENCY_NP = np.array(SHARED_ADJACENCY, copy=False)
        SHARED_ADJACENCY_NP.shape = [-1, 3]

        global set_item_adj
        set_item_adj = functools.partial(operator.setitem, SHARED_ADJACENCY_NP)

        global SHARED_NORMALS_NP
        SHARED_NORMALS_NP = np.array(SHARED_NORMALS, copy=False)
        SHARED_NORMALS_NP.shape = [-1, 3]


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
    import time

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

    def make_chunks_aligned(chunk_size, length, values):
        def align(index):
            if index == 0 or index >= len(values):
                return index
            eq_start = functools.partial(operator.eq, values[index][0])
            iterator = itertools.dropwhile(
                lambda x: eq_start(x[1][0]), enumerate(values[index:], index)
            )
            return next(iterator)[0]

        return (
            (align(start), align(stop))
            for start, stop in make_chunks(chunk_size, length)
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
        if USE_NUMPY:
            shared["hashes"] = ctx.RawArray("l", count_facets * 3)
            shared["hashes_indices"] = ctx.RawArray("l", count_facets * 3)
            shared["pairs"] = ctx.RawArray(
                "l", int(count_facets * 1.2) * 3 * 2
            )
            shared["current_pair"] = ctx.Value("l", 0)

        tick("prepare shared")
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")

            # Compute adjacency
            if USE_NUMPY:
                count_edges = count_facets * 3
                chunks = make_chunks(chunk_size, count_edges)
                run_unordered(pool, compute_hashes_np, chunks)
                tick("hashes (mp/np)")

                # Sort hashes
                hashes = np.array(shared["hashes"])
                hashes_indices = np.argsort(hashes)
                hashes = hashes[hashes_indices]
                shared["hashes"][:] = hashes
                shared["hashes_indices"][:] = hashes_indices
                tick("sorted hashes (mp/np)")

                # Build pairs
                chunks = make_chunks(chunk_size, count_edges)
                run_unordered(pool, build_pairs_np, chunks)
                current_pair = shared["current_pair"].value
                tick(f"pairs ({current_pair}) (mp/np)")

                # Sort pairs
                facet_pairs = np.array(shared["pairs"])
                facet_pairs.reshape(-1, 2)
                facet_pairs.resize((current_pair, 2))
                facet_pairs = facet_pairs[np.lexsort(facet_pairs.T[::-1])]
                shared["pairs"][: current_pair * 2] = facet_pairs.flatten()
                tick("sorted pairs (mp/np)")

                # Compute adjacency
                chunks = make_chunks_aligned(
                    chunk_size, len(facet_pairs), facet_pairs
                )
                run_unordered(pool, compute_adjacents_np, chunks)
                tick("adjacency (mp/np)")
            else:
                chunks = make_chunks(chunk_size, count_facets)
                func, tickmsg = compute_adjacents, "adjacency"
                run_unordered(pool, func, chunks)
                tick(tickmsg)

            # Compute connected components
            chunks = make_chunks(len(facets) // nproc, len(facets) // 3)
            run_unordered(pool, connected_components_chunk, chunks)

            tick("connected components (pass #1 - map)")

            # Update subcomponents
            tags = shared["tags"]

            maxtag = shared["current_tag"].value
            subcomponents = [[] for i in range(maxtag)]
            subadjacency = [[] for i in range(maxtag)]

            for ifacet, tag in enumerate(tags):
                subcomponents[tag].append(ifacet)

            # Update adjacents
            l2struct = struct.Struct("ll")

            not_zero = functools.partial(operator.ne, (0, 0))
            iterator = itertools.takewhile(
                not_zero,
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
            for index, tag in enumerate(tags):
                out_tags[index] = final_tags[tag]

            tick("connected components (pass #2 - reduce & write)")

    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin


# *****************************************************************************

if __name__ == "__main__":
    # pylint: disable=used-before-assignment
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
