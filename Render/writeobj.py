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
import functools

# Init
def init(*args):
    """Initialize pool."""
    # pylint: disable=global-variable-undefined
    # pylint: disable=invalid-name
    global fmt_v, fmt_vt, fmt_vn, fmt_f, join_f, mask_f
    fmt_v = functools.partial(str.format, "v {} {} {}\n")
    fmt_vt = functools.partial(str.format, "vt {} {}\n")
    fmt_vn = functools.partial(str.format, "vn {} {} {}\n")
    mask_f, *_ = args
    fmt_f = functools.partial(str.format, mask_f)
    join_f = functools.partial(str.join, "")


# Vertices
def func_v(val):
    """Write vertex."""
    return fmt_v(*val)


# UV map
def func_vt(val):
    """Write uv."""
    return fmt_vt(*val)


# Normals
def func_vn(val):
    """Write normal."""
    return fmt_vn(*val)


# Faces
def func_f(val):
    """Write face."""
    return join_f(["f"] + [fmt_f(x + 1) for x in val] + ["\n"])


# String
def func_s(val):
    """Write plain string (nop)."""
    return val


# Main
if __name__ == "__main__":
    import os
    import shutil
    import itertools

    # Set directory and stdout
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set executable
    executable = shutil.which("pythonw")
    if not executable:
        executable = shutil.which("python")
        if not executable:
            raise RuntimeError("No Python executable")
    mp.set_executable(executable)
    mp.set_start_method("spawn", force=True)

    # Get variables
    # pylint: disable=used-before-assignment
    try:
        inlist
    except NameError:
        inlist = [([(1, 2, 3)] * 2000000, "v")]  # Debug purpose

    try:
        mask
    except NameError:
        mask = ""  # pylint: disable=invalid-name

    try:
        objfile
    except NameError:
        objfile = "tmp.obj"  # pylint: disable=invalid-name

    # Parse format
    functions = {
        "v": func_v,
        "vt": func_vt,
        "vn": func_vn,
        "f": func_f,
        "s": func_s,
    }

    CHUNK_SIZE = 20000
    NPROC = os.cpu_count()

    # Run
    try:
        with mp.Pool(NPROC, init, (mask,)) as pool:
            result = (
                pool.imap(functions[fmt], values, CHUNK_SIZE)
                for values, fmt in inlist
            )
            result = itertools.chain.from_iterable(result)
            with open(objfile, "w", encoding="utf-8") as f:
                f.writelines(result)
    finally:
        os.chdir(save_dir)
