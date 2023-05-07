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
import traceback
import array
from math import cos
from itertools import permutations, groupby, starmap
from multiprocessing import shared_memory


try:
    import numpy as np
    from numpy import bitwise_or, left_shift

    USE_NUMPY = True
except ModuleNotFoundError:
    USE_NUMPY = False

sys.path.insert(0, os.path.dirname(__file__))
# pylint: disable=wrong-import-position
import vector3d
from vector3d import (
    fmul,
    angles,
    safe_normalize,
)


def getpoint(idx):
    """Get a point from its index in the shared memory."""
    idx *= 3
    return SHARED_POINTS[idx], SHARED_POINTS[idx + 1], SHARED_POINTS[idx + 2]


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
        and dot(getnormal(facet_idx + start), getnormal(other_idx)) >= split_angle_cos
    )

    add = list.append
    any(itertools.starmap(add, iterator))  # Sorry, we use side effect (faster)...

    SHARED_ADJACENCY[start * 3 : stop * 3] = [
        a
        for adj in adjacents
        for a in itertools.islice(itertools.chain(set(adj), (-1, -1, -1)), 0, 3)
    ]


# *****************************************************************************


def compute_hashes_np(chunk):
    """Compute hash keys for chunk

    Numpy version
    """
    start, stop = chunk

    hashes = bitwise_or(
        left_shift(ALL_EDGES_LEFT[start:stop], 32, dtype=np.int64),
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
    facet_pairs = np.stack((INDICES_NP[pairs["x"]], INDICES_NP[pairs["y"]]), axis=-1)

    # Filter angle
    split_angle_cos = cos(SHARED_SPLIT_ANGLE.value)
    dotprod = np.einsum(
        "ij,ij->i",
        SHARED_NORMALS_NP[facet_pairs[..., 0]],
        SHARED_NORMALS_NP[facet_pairs[..., 1]],
    )
    facet_pairs = np.compress(dotprod >= split_angle_cos, facet_pairs, axis=0)

    # Write shared memory
    shm = shared_memory.SharedMemory(create=True, size=facet_pairs.nbytes)
    np_buffer = np.ndarray(facet_pairs.shape, dtype=facet_pairs.dtype, buffer=shm.buf)
    np_buffer[:] = facet_pairs[:]  # Copy the original data into shared memory
    name = shm.name

    # We must keep a handle of shm, otherwise it is automatically closed
    # when the function exits
    # https://stackoverflow.com/questions/74193377/filenotfounderror-when-passing-a-shared-memory-to-a-new-process
    global SHARED_MEMS
    SHARED_MEMS.append(shm)

    # Clean and return information to calling process
    return name, np_buffer.shape


def compute_adjacents_np(chunk):
    """Compute adjacency lists - numpy version."""
    start, stop = chunk

    # Get pairs
    shm_name = bytearray(SHARED_PAIRS_SHM_NAME).rstrip(b"\0").decode()
    shm = shared_memory.SharedMemory(name=shm_name, create=False)
    pairs = np.frombuffer(shm.buf, dtype=np.int32)
    pairs.shape = (-1, 2)

    pairs = pairs[start:stop]

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
    shared_current_tag = shared["current_tag"] if shared else SHARED_CURRENT_TAG

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
        if 0 <= f < start or f >= stop
    }
    adjacents2 = list(itertools.chain.from_iterable(adjacents2))

    shared_current_adj = SHARED_CURRENT_ADJ
    with shared_current_adj:
        offset = shared_current_adj.value
        shared_current_adj.value += len(adjacents2)
        SHARED_ADJACENCY2[offset : offset + len(adjacents2)] = adjacents2


# *****************************************************************************
def slice2d(sliceable, start, stop, group_by_n):
    """Emulate 2D slicing.
    
    Roughly equivalent to sliceable[start, stop] if shape of sliceable
    is (..., group_by_n).
    """
    sliceable = sliceable[start * group_by_n : stop * group_by_n] 
    iters = [iter(sliceable)] * group_by_n
    return zip(*iters)

# TODO
def getfacet(idx):
    """Get a facet from its index in the shared memory."""
    idx *= 3
    return SHARED_FACETS[idx], SHARED_FACETS[idx + 1], SHARED_FACETS[idx + 2]

def getarea(idx):
    """Get a normal from its index in the shared memory."""
    return SHARED_AREAS[idx]

def compute_weighted_normals(chunk):
    """Compute weighted normals for each point."""
    start, stop = chunk

    it_facets = zip(
        slice2d(SHARED_FACETS, start, stop, 3),
        slice2d(SHARED_NORMALS, start, stop, 3),
        SHARED_AREAS[start:stop]
    )
    # TODO:
    it_facets = list(it_facets)
    print(len(it_facets))

    # TODO Replace
    it_facets = (
        (getfacet(i), getnormal(i), getarea(i)) for i in range(start, stop)
    )

    # TODO
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


def compute_weighted_normals_np(chunk):
    """Compute weighted normals for each point (numpy version)."""
    start, stop = chunk

    # TODO
    points = np.asarray(SHARED_POINTS, dtype="f4")
    points = np.reshape(points, [-1, 3])

    facets = np.asarray(SHARED_FACETS, dtype="i4")
    facets = np.reshape(facets, [-1, 3])
    facets = facets[start:stop, ...]

    areas = np.asarray(SHARED_AREAS, dtype="f4")
    areas = areas[start:stop, ...]

    normals = np.asarray(SHARED_NORMALS, dtype="f4")
    normals = np.reshape(normals, [-1, 3])
    normals = normals[start:stop, ...]

    triangles = np.take(points, facets, axis=0)
    indices = facets.ravel(order="F")

    def _safe_normalize(vect_array):
        """Safely normalize an array of vectors."""
        magnitudes = np.sqrt((vect_array**2).sum(-1))
        magnitudes = np.expand_dims(magnitudes, axis=1)
        return np.divide(vect_array, magnitudes, where=magnitudes != 0.0)

    def _angles(i, j, k):
        """Compute triangle vertex angles."""
        # Compute normalized vectors
        vec1 = triangles[::, j, ::] - triangles[::, i, ::]
        vec1 = _safe_normalize(vec1)

        vec2 = triangles[::, k, ::] - triangles[::, i, ::]
        vec2 = _safe_normalize(vec2)

        # Compute dot products
        # (Clip to avoid precision issues)
        dots = (vec1 * vec2).sum(axis=1).clip(-1.0, 1.0)

        # Compute arccos of dot products
        return np.arccos(dots)

    # Compute vertex angles
    # Reminder:
    # local a1 = AngleBetweenVectors (v1-v0) (v2-v0)
    # local a2 = AngleBetweenVectors (v0-v1) (v2-v1)
    # local a3 = AngleBetweenVectors (v0-v2) (v1-v2)
    angles0 = _angles(0, 1, 2)
    angles1 = _angles(1, 0, 2)
    angles2 = np.pi - angles1 - angles0
    # Debug
    # assert np.all(np.isclose(angles0+angles1+_angles(2, 0, 1),np.pi))
    vertex_angles = np.concatenate((angles0, angles1, angles2))

    # Compute weighted normals for each vertex of the triangles
    vertex_areas = np.concatenate((areas, areas, areas))
    weights = vertex_areas * vertex_angles
    weights = np.expand_dims(weights, axis=1)

    vertex_normals = np.concatenate((normals, normals, normals), axis=0)
    weighted_normals = vertex_normals * weights

    return indices, weighted_normals


# *****************************************************************************

def normalize(chunk):
    """Normalize normal vectors."""
    start, stop = chunk

    fmt = "fff"
    f3struct = struct.Struct(fmt)
    f3pack = f3struct.pack
    f3iter_unpack = f3struct.iter_unpack
    f3itemsize = struct.calcsize(fmt)

    # vnormals = memoryview(SHARED_VNORMALS).cast("b")[  # TODO
    vnormals = memoryview(SHARED["vnormals"]).cast("b")[
        start * f3itemsize : stop * f3itemsize
    ]

    result = b"".join(
        f3pack(*safe_normalize(v)) for v in f3iter_unpack(vnormals)
    )

    vnormals[::] = memoryview(result).cast("b")


def normalize_np(chunk):
    """Normalize normal vectors - Numpy version."""
    start, stop = chunk
    shared_vnormals = SHARED["vnormals"]
    vnormals = np.asarray(shared_vnormals[start * 3 : stop * 3], dtype="f4")
    vnormals = np.reshape(vnormals, [stop - start, 3])

    magnitudes = np.sqrt((vnormals**2).sum(-1))
    magnitudes = np.expand_dims(magnitudes, axis=1)
    vnormals = np.divide(vnormals, magnitudes, where=magnitudes != 0.0)


# *****************************************************************************

def init(shared):
    """Initialize pool of processes."""
    gc.disable()

    # pylint: disable=global-variable-undefined
    global SHARED
    SHARED = shared

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
        SHARED_HASHES_INDICES_NP = np.array(shared["hashes_indices"], copy=False)

        count_facets = len(SHARED_FACETS) // 3  # TODO Remove

        facets = np.array(SHARED_FACETS, copy=True)
        facets.shape = [-1, 3]
        facets.sort(axis=1)

        global SHARED_MEMS
        SHARED_MEMS = []

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

        global SHARED_PAIRS_SHM_NAME
        SHARED_PAIRS_SHM_NAME = shared["pairs_shm_name"]

        global SHARED_ADJACENCY_NP
        SHARED_ADJACENCY_NP = np.array(SHARED_ADJACENCY, copy=False)
        SHARED_ADJACENCY_NP.shape = [-1, 3]

        global set_item_adj
        set_item_adj = functools.partial(operator.setitem, SHARED_ADJACENCY_NP)

        global SHARED_NORMALS_NP
        SHARED_NORMALS_NP = np.array(SHARED_NORMALS, copy=False)
        SHARED_NORMALS_NP.shape = [-1, 3]


def reinit(shared):
    """Reinitialize global data."""
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


def main(python, points, facets, normals, areas, uvmap, split_angle, showtime):
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
            "\nCONNECTED COMPONENTS\n"
            f"start adjacency computation: {len(points) // 3} points, "
            f"{len(facets) // 3} facets"
        )
        print(msg)

    def tick(msg=""):
        """Print the time (debug purpose)."""
        if showtime:
            print(msg, time.time() - tm0)

    def make_chunks(chunk_size, length):
        return ((i, min(i + chunk_size, length)) for i in range(0, length, chunk_size))

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
        result = [r for r in imap]
        if any(result):
            print("Not null result")

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
            "tags": ctx.RawArray("l", count_facets),
            "current_tag": ctx.Value("l", 0),
            "current_adj": ctx.Value("l", 0),
        }
        if USE_NUMPY:
            shared["hashes"] = ctx.RawArray("q", count_facets * 3)
            shared["hashes_indices"] = ctx.RawArray("l", count_facets * 3)
            shared["current_pair"] = ctx.Value("l", 0)  # TODO Remove
            shared["pairs_shm_name"] = ctx.RawArray("b", 256)

        tick("prepare shared")
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")

            # Compute adjacency
            if USE_NUMPY:
                # # Debug
                # print(
                # np.sort(
                # np.frombuffer(facets, dtype=np.int32).reshape([-1,3]),
                # axis=1,
                # )
                # )

                # Compute edges (with unique key: "hash")
                count_edges = count_facets * 3
                chunks = make_chunks(chunk_size, count_edges)
                run_unordered(pool, compute_hashes_np, chunks)
                tick("hashes (mp/np)")

                # Sort hashes
                hashes = np.array(shared["hashes"], dtype=np.int64)
                hashes_indices = np.argsort(hashes)
                hashes = hashes[hashes_indices]
                shared["hashes"][:] = hashes
                shared["hashes_indices"][:] = hashes_indices % count_facets
                tick("sorted hashes (mp/np)")

                # Build pairs
                chunks = make_chunks(chunk_size, count_edges)
                imap = pool.imap_unordered(build_pairs_np, chunks)
                results = [
                    (shared_memory.SharedMemory(name=n, create=False), s)
                    for n, s in imap
                ]

                np_bufs = [
                    np.ndarray(shape, dtype=np.int32, buffer=shm.buf)
                    for shm, shape in results
                ]
                facet_pairs = np.concatenate(np_bufs)

                # Close and clean shared memory
                for shm, _ in results:
                    shm.close()
                    shm.unlink()
                tick(f"pairs ({len(facet_pairs)}) (mp/np)")

                # Sort pairs
                facet_pairs = facet_pairs[np.lexsort(facet_pairs.T[::-1])]

                # # Check symmetry in pairs (debug)
                # reverse_pairs = np.array(np.flip(facet_pairs, axis=1), copy=True)
                # facet_pairs2 = np.array(facet_pairs, copy=True)
                # dt = [("x", np.int32), ("y", np.int32)]
                # facet_pairs2.dtype = dt
                # reverse_pairs.dtype = dt
                # notisin = np.logical_not(np.isin(reverse_pairs, facet_pairs2))
                # print(
                # "check symmetry (ok if empty)",
                # np.argwhere(notisin),
                # len(np.argwhere(notisin))
                # )

                # Create shared object for adjacency
                shm = shared_memory.SharedMemory(create=True, size=facet_pairs.nbytes)
                buf_np = np.ndarray(
                    facet_pairs.shape, dtype=facet_pairs.dtype, buffer=shm.buf
                )
                buf_np[:] = facet_pairs[:]
                name = str.encode(shm.name)
                assert len(name) < 255
                shared["pairs_shm_name"][: len(name)] = name
                tick("sorted pairs (mp/np)")

                # Initialize adjacency
                adj = np.ndarray(
                    buffer=shared["adjacency"],
                    shape=(count_facets * 3,),
                    dtype=np.int32,
                )
                adj[:] = -1

                # Compute adjacency
                chunks = make_chunks_aligned(chunk_size, len(facet_pairs), facet_pairs)
                run_unordered(pool, compute_adjacents_np, chunks)
                tick("adjacency (mp/np)")
            else:
                chunks = make_chunks(chunk_size, count_facets)
                run_unordered(pool, compute_adjacents, chunks)
                tick("adjacency")

            # # Debug
            # # Check symmetry in adjacency
            # adj = shared["adjacency"]
            # error = 0
            # for ifacet in range(0, count_facets):
            # for f in adj[ifacet*3 : ifacet*3+3]:
            # if f!=-1 and not ifacet in adj[f*3:f*3+3] and error < 100:
            # print(
            # "ERROR #1:",
            # ifacet,
            # f,
            # list(adj[ifacet*3: ifacet*3+3])
            # )
            # error += 1

            # Compute connected components
            # Compute also pass#2 adjacency lists ("adjacency2")
            chunks = make_chunks(len(facets) // nproc, len(facets) // 3)
            run_unordered(pool, connected_components_chunk, chunks)

            tick("connected components (pass #1 - map)")

            # Update subcomponents
            tags_pass1 = shared["tags"]

            maxtag = shared["current_tag"].value
            subcomponents = [[] for i in range(maxtag)]
            subadjacency = [[] for i in range(maxtag)]

            for ifacet, tag in enumerate(tags_pass1):
                subcomponents[tag].append(ifacet)

            # Update adjacents
            l2struct = struct.Struct("ll")
            not_zero = functools.partial(operator.ne, (0, 0))
            iterator = filter(
                not_zero,
                l2struct.iter_unpack(shared["adjacency2"]),
            )
            iterator = ((tag, tags_pass1[ifacet]) for tag, ifacet in iterator)
            iterator = (
                (tag, other_tag) for tag, other_tag in iterator if tag != other_tag
            )
            for tag, other_tag in iterator:
                subadjacency[tag].append(other_tag)

            tick("connected components (pass #1 - reduce)")

            # # Debug
            # # Check symmetry in adjacency pass#2
            # error = 0
            # for ifacet, adjs in enumerate(subadjacency):
            # for f in adjs:
            # if not ifacet in subadjacency[f] and error < 100:
            # print("ERROR", ifacet, f)
            # error += 1

            tags_pass2 = connected_components(subadjacency, shared=shared)
            tick("connected components (pass #2 - map)")

            # Update and write tags
            tags = shared["tags"]
            for index, tag in enumerate(tags_pass1):
                tags[index] = tags_pass2[tag]

            tick("connected components (pass #2 - reduce & write)")

            # Recompute Points & Facets

            # TODO
            print("distinct tags", len(set(tags)))

            # Recompute points
            l3struct = struct.Struct("lll")
            l3iter_unpack = l3struct.iter_unpack
            newpoints = {
                (point_index, tag): None
                for facet, tag in zip(l3iter_unpack(facets), tags)
                for point_index in facet
            }

            # Number newpoint
            for index, point in enumerate(newpoints):
                newpoints[point] = index

            # Rebuild point list
            # TODO Parallelize
            point_list = [
                c
                for point_index, tag in newpoints
                for c in points[3 * point_index:3 * point_index + 3]
            ]
            points = mp.RawArray("f", len(newpoints) * 3)
            points[:] = point_list
            shared["points"] = points
            tick(f"new points ({len(newpoints)})")

            # If necessary, rebuild uvmap
            if uvmap:
                uvmap_list = [
                    c 
                    for point_index, tag in newpoints
                    for c in uvmap[point_index * 2: point_index * 2 +2 ]
                ]
                uvmap = mp.RawArray("f", len(newpoints) *2)
                uvmap[:] = uvmap_list
            tick(f"rebuild uvmap ({uvmap})")

            # Update point indices in facets
            facet_list = [
                newpoints[point_index, tag] 
                for facet, tag in zip(l3iter_unpack(facets), tags)
                for point_index in facet
            ]
            assert len(facet_list) // 3 == count_facets
            facets = mp.RawArray("l", len(facet_list))
            facets[:] = facet_list
            shared["facets"] = facets
            tick(f"updated facets")


        # Vertex Normals Computation

        shared["vnormals"] = mp.RawArray("f", len(points))

        # TODO We have to restart pool
        with ctx.Pool(nproc, init, (shared,)) as pool:
            tick("start pool")

            # Compute weighted normals (n per vertex)
            chunks = make_chunks(chunk_size, len(facets) // 3)
            func = (
                compute_weighted_normals_np
                if USE_NUMPY
                else compute_weighted_normals
            )
            data = pool.imap_unordered(func, chunks)

            # Reduce weighted normals (one per vertex)
            vnorms = shared["vnormals"]
            if not USE_NUMPY:
                wstruct = struct.Struct("lfff")
                for chunk in data:
                    for point_index, *weighted_vnorm in wstruct.iter_unpack(
                        chunk
                    ):
                        offset = point_index * 3
                        vnorms[offset] += weighted_vnorm[0]
                        vnorms[offset + 1] += weighted_vnorm[1]
                        vnorms[offset + 2] += weighted_vnorm[2]
            else:
                indices, normals = zip(*data)
                indices = np.concatenate(indices)
                normals = np.concatenate(normals)
                normals = np.column_stack(
                    (
                        np.bincount(indices, normals[..., 0]),
                        np.bincount(indices, normals[..., 1]),
                        np.bincount(indices, normals[..., 2]),
                    )
                )
                vnorms[: normals.size] = list(normals.flat)

            tick("reduce weighted normals")

            # Normalize
            chunks = make_chunks(chunk_size, len(points) // 3)
            func = normalize_np if USE_NUMPY else normalize
            run_unordered(pool, func, chunks)
            tick("normalize")

            # Write output buffers (points, facets, uvmap, vnormals)
            def create_shm(obj):
                memv = memoryview(obj)
                size = memv.nbytes
                if size > 0:
                    shm =shared_memory.SharedMemory(create=True, size=size)
                    shm.buf[:] = memv.tobytes()
                else:
                    shm = None
                return shm
            points_shm = create_shm(points)
            facets_shm = create_shm(facets)
            vnormals_shm = create_shm(vnorms)
            uvmap_shm = create_shm(uvmap)

            tick("write output buffers")

        output = [points_shm.name, facets_shm.name, vnormals_shm.name]
        if uvmap_shm:
            output.append(uvmap_shm.name)
        CONNECTION.send(output)
        CONNECTION.recv()
        tick("send output buffers")

        input("Press Enter to continue...")  # Debug

    except Exception as exc:
        print(traceback.format_exc())
        input("Press Enter to continue...")  # Debug
        raise exc
    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin


# *****************************************************************************

if __name__ == "__main__":
    try:
        # pylint: disable=used-before-assignment
        main(PYTHON, POINTS, FACETS, NORMALS, AREAS, UVMAP, SPLIT_ANGLE, SHOWTIME)

        # Clean (remove references to foreign objects)
        PYTHON = None
        POINTS = None
        FACETS = None
        NORMALS = None
        AREAS = None
        UVMAP = None
        SPLIT_ANGLE = None
        SHOWTIME = None
    except Exception:
        pass
