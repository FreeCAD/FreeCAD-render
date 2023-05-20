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
    global fmt_v, fmt_vt, fmt_vn, fmt_f, join_f
    fmt_v = functools.partial(str.format, "v {:g} {:g} {:g}\n")
    fmt_vt = functools.partial(str.format, "vt {:g} {:g}\n")
    fmt_vn = functools.partial(str.format, "vn {:g} {:g} {:g}\n")
    fmt_f = functools.partial(str.format, mask_f)
    join_f = functools.partial(str.join, "")


# Faces
def func_f(*val):
    """Write face."""
    return join_f(["f"] + [fmt_f(x + 1) for x in val] + ["\n"])


def create_shm(obj, empty=False):
    """Create a SharedMemory object from the argument.

    The argument must support buffer protocol.
    The shared memory is created with the adequate size to host the
    argument.
    If empty==False (default), the shared memory is initialized with the
    argument content. Otherwise it is kept uninitialized
    """
    memv = memoryview(obj)
    size = memv.nbytes
    if size > 0:
        shm = SHARED_SMM.SharedMemory(size)
        if not empty:
            shm.buf[:] = memv.tobytes()
    else:
        shm = None
    return shm


def format_chunk(shared_array, group, format_function, chunk):
    start, stop = chunk

    # Format string
    elems = (
        shared_array[group * i : group * i + group] for i in range(start, stop)
    )
    lines = (format_function(*e) for e in elems)
    concat = "".join(lines)
    concat = concat.encode("utf-8")

    # Write shared memory
    shm = create_shm(concat)
    name = shm.name

    return name, len(concat)


def format_points(chunk):
    return format_chunk(SHARED_POINTS, 3, fmt_v, chunk)


def format_uvmap(chunk):
    return format_chunk(SHARED_UVMAP, 2, fmt_vt, chunk)


def format_vnormals(chunk):
    return format_chunk(SHARED_VNORMALS, 3, fmt_vn, chunk)


def format_facets(chunk):
    return format_chunk(SHARED_FACETS, 3, func_f, chunk)


# Main
if __name__ == "__main__":
    import os
    import sys
    import itertools
    import time

    tm0 = time.time()
    if SHOWTIME:
        msg = "\nWRITE OBJ"
        print(msg)

    def tick(msg=""):
        """Print the time (debug purpose)."""
        if SHOWTIME:
            print(msg, time.time() - tm0)

    # Get variables
    # pylint: disable=used-before-assignment
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
        return (
            (i, min(i + chunk_size, length))
            for i in range(0, length, chunk_size)
        )

    chunk_size = 20000

    # Run
    try:
        shared = {
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
            mask = " {0}/{0}/{0}"
        elif not HAS_VNORMALS and HAS_UVMAP:
            mask = " {0}/{0}"
        elif HAS_VNORMALS and not HAS_UVMAP:
            mask = " {0}//{0}"
        else:
            mask = " {}"

        with SharedMemoryManager() as smm:
            tick("shared memory manager started")
            pool_args = (mask, shared, smm.address)
            with mp.Pool(NPROC, init, pool_args) as pool:
                tick("pool started")
                with open(OBJFILE, "w+b") as f:

                    def write_array(name, format_function, item_number):
                        chunks = make_chunks(chunk_size, item_number)
                        buffers = pool.imap(format_function, chunks)
                        results = (
                            (SharedMemory(name=n, create=False), s)
                            for n, s in buffers
                        )
                        results = (
                            shm.buf[0:s].tobytes()
                            for shm, s in results
                        )
                        msg = f"# {name}\n"
                        f.write(msg.encode("utf-8"))
                        f.writelines(results)
                        tick(name.lower())

                    # Write header & mtl
                    f.write("# Written by FreeCAD-Render\n".encode("utf-8"))
                    if MTLFILENAME:
                        mtl = f"mtllib {MTLFILENAME}\n\n"
                        f.write(mtl.encode("utf-8"))

                    # Write vertices (points)
                    write_array("Vertices", format_points, count_points)

                    # Write uv
                    if HAS_UVMAP:
                        write_array(
                            "Uv map", format_uvmap, count_uvmap
                        )

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
