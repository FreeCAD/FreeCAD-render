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

"""Script for points transformation in multiprocessing mode."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from vector3d import add, sub, fmul, fdiv, barycenter, length, normal, transform

def transform_points(matrix, points):
    """Transform points with a transformation matrix 4x4."""
    return [transform(matrix, point) for point in points]


def main(python, matrix, points, showtime):
    """Main entry point for main process."""
    # pylint: disable=import-outside-toplevel
    import multiprocessing as mp
    from functools import partial
    import time
    import os
    import sys
    import shutil
    import itertools

    tm0 = time.time()
    def tick(msg=""):
        """Print the time (debug purpose)."""
        if showtime:
            print(msg, time.time() - tm0)

    # Only >= 3.8
    def batched(iterable, number):
        "Batch data into lists of length n. The last batch may be shorter."
        # batched('ABCDEFG', 3) --> ABC DEF G
        # from Python itertools documentation...
        iterator = iter(iterable)
        while batch := list(itertools.islice(iterator, number)):
            yield batch

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

    # TODO Move elsewhere
    def grouper(iterable, number, fillvalue=None):
        "Collect data into fixed-length chunks or blocks"
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * number
        return itertools.zip_longest(*args, fillvalue=fillvalue)

    transmat = tuple(grouper(matrix.A, 4))

    # Run
    try:
        tick("start pool")
        with ctx.Pool(nproc) as pool:
            # Transform points (with transmat)
            _transform_points = partial(transform_points, transmat)
            output = pool.imap(_transform_points, batched(POINTS, chunk_size))
            points = sum(output, [])
        tick("get points")
    finally:
        os.chdir(save_dir)
        sys.stdin = save_stdin

    return points


if __name__ == "__main__":

    # Get variables
    # pylint: disable=used-before-assignment
    try:
        POINTS
    except NameError:
        POINTS = []

    try:
        TRANSMAT
    except NameError:
        TRANSMAT = None

    try:
        SHOWTIME
    except NameError:
        SHOWTIME = False

    assert PYTHON, "No Python executable provided."

    SHOWTIME = True  # TODO Debug
    POINTS = main(PYTHON, TRANSMAT, POINTS, SHOWTIME)
