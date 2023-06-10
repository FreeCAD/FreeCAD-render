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

"""This script writes an OBJ file in a multiprocessing approach.

It is a helper for Rendermesh._write_objfile_mp.
"""

import multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory
from multiprocessing.managers import SharedMemoryManager
import functools
import operator


# Init
def init(*args):
    """Initialize pool."""
    mask_f, shared, smm_address, *_ = args

    # pylint: disable=global-variable-undefined
    global SHARED_POINTS
    SHARED_POINTS = shared["points"]

    global SHARED_FACETS
    SHARED_FACETS = shared["facets"]

    global SHARED_VNORMALS
    SHARED_VNORMALS = shared["vnormals"]

    global SHARED_UVMAP
    SHARED_UVMAP = shared["uvmap"]

    global SHARED_SMM
    SHARED_SMM = SharedMemoryManager(address=smm_address)

    # pylint: disable=invalid-name
    global fmt_v, fmt_vt, fmt_vn, fmt_f, join_f, add1
    fmt_f = functools.partial(str.format, mask_f)
    join_f = functools.partial(str.join, "")
    fmt_v = b"v %g %g %g\n".__mod__
    fmt_vt = b"vt %g %g\n".__mod__
    fmt_vn = b"vn %g %g %g\n".__mod__
    add1 = functools.partial(operator.add, 1)

    global SHMS
    SHMS = []



# Faces
def func_f(val):
    """Write face."""
    return join_f(["f"] + list(map(fmt_f, val)) + ["\n"]).encode("utf-8")


def format_chunk(shared_array, group, format_function, chunk):
    """Format a chunk of data, from an array."""
    start, stop = chunk

    # Format string
    elems = (
        shared_array[group * i : group * i + group] for i in range(start, stop)
    )
    lines = (format_function(tuple(e)) for e in elems)
    concat = b"".join(lines)

    # Write shared memory
    shm = SHARED_SMM.SharedMemory(len(concat))
    shm.buf[:] = concat
    name = shm.name
    global SHMS
    SHMS.append(shm)

    return name, len(concat)


def format_points(chunk):
    """Format a chunk of points."""
    return format_chunk(SHARED_POINTS, 3, fmt_v, chunk)


def format_uvmap(chunk):
    """Format a chunk of uv."""
    return format_chunk(SHARED_UVMAP, 2, fmt_vt, chunk)


def format_vnormals(chunk):
    """Format a chunk of vertex normals."""
    return format_chunk(SHARED_VNORMALS, 3, fmt_vn, chunk)


def format_facets(chunk):
    """Format a chunk of facets."""
    start, stop = chunk
    # First, we must increment facet indices, as OBJ format requires indices to
    # start at 1...
    incremented_facets = list(map(add1, SHARED_FACETS[start * 3 : stop * 3]))
    chunk2 = (0, stop - start)
    # Then we format
    return format_chunk(incremented_facets, 3, func_f, chunk2)


# Main
if __name__ == "__main__":
    import os
    import sys
    import time

    # pylint: disable=used-before-assignment
    tm0 = time.time()
    if SHOWTIME:
        print("\nWRITE OBJ")

    def tick(message=""):
        """Print the time (debug purpose)."""
        if SHOWTIME:
            print(message, time.time() - tm0)

    # Get variables
    try:
        PYTHON
    except NameError:
        PYTHON = None  # pylint: disable=invalid-name

    assert PYTHON, "No Python executable provided."

    # Set working directory
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set stdin
    save_stdin = sys.stdin
    sys.stdin = sys.__stdin__

    # Set executable
    mp.set_executable(PYTHON)
    mp.set_start_method("spawn", force=True)

    CHUNK_SIZE = 20000
    NPROC = os.cpu_count()

    def make_chunks(chunk_size, length):
        """Compute a tuple (start, stop) to define a chunk."""
        return (
            (i, min(i + chunk_size, length))
            for i in range(0, length, chunk_size)
        )

    # Run
    try:
        SHARED = {
            "points": POINTS,
            "facets": FACETS,
            "vnormals": VNORMALS,
            "uvmap": UVMAP,
        }
        count_points = len(POINTS) // 3
        count_facets = len(FACETS) // 3
        count_vnormals = len(VNORMALS) // 3
        count_uvmap = len(UVMAP) // 2

        # Mask for facets
        if HAS_VNORMALS and HAS_UVMAP:
            MASK = " {0}/{0}/{0}"
        elif not HAS_VNORMALS and HAS_UVMAP:
            MASK = " {0}/{0}"
        elif HAS_VNORMALS and not HAS_UVMAP:
            MASK = " {0}//{0}"
        else:
            MASK = " {}"

        with SharedMemoryManager() as smm:
            tick("shared memory manager started")
            pool_args = (MASK, SHARED, smm.address)
            with mp.Pool(NPROC, init, pool_args) as pool:
                tick("pool started")
                with open(OBJFILE, "w+b") as f:

                    def write_array(name, format_function, item_number):
                        """Write an array to disk, using a format."""
                        chunks = make_chunks(CHUNK_SIZE, item_number)
                        buffers = pool.imap(format_function, chunks)
                        results = (
                            (SharedMemory(name=n, create=False), s)
                            for n, s in buffers
                        )
                        results = (
                            shm.buf[0:s].tobytes() for shm, s in results
                        )
                        msg = f"# {name}\n"
                        f.write(msg.encode("utf-8"))
                        f.writelines(results)
                        tick(name.lower())

                    # Write header & mtl
                    f.write(
                        "# Written by FreeCAD-Render (mp)\n".encode("utf-8")
                    )
                    if MTLFILENAME:
                        mtl = f"mtllib {MTLFILENAME}\n\n"
                        f.write(mtl.encode("utf-8"))

                    # Write vertices (points)
                    write_array("Vertices", format_points, count_points)

                    # Write uv
                    if HAS_UVMAP:
                        write_array("Uv map", format_uvmap, count_uvmap)

                    # Write vertex normals
                    if HAS_VNORMALS:
                        write_array(
                            "Vertex normals", format_vnormals, count_vnormals
                        )

                    # Write object statement
                    f.write(f"o {OBJNAME}\n".encode("utf-8"))
                    if MTLNAME is not None:
                        f.write(f"usemtl {MTLNAME}\n".encode("utf-8"))

                    # Write facets
                    write_array("Faces", format_facets, count_facets)

    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin
        # Release shared variables
        POINTS = None
        FACETS = None
        VNORMALS = None
        UVMAP = None
        SHOWTIME = None
        OBJFILE = None
        HAS_VNORMALS = None
        HAS_UVMAP = None
        OBJNAME = None
        MTLFILENAME = None
        MTLNAME = None
