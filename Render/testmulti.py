import multiprocessing as mp
from multiprocessing import spawn
import sys
import os
import shutil


def foo():
    print("Entering foo")
    for i in range(2):
        pass


if __name__ == '__main__':
    print("Entering main")
    os.chdir("/home/vincent/Documents/DevGit/FreeCAD-render/Render")
    executable = shutil.which("python")
    mp.set_executable(executable)
    mp.set_start_method('spawn', force=True)
    stdin = sys.stdin
    sys.stdin = sys.__stdin__
    vertices = [(1,2,3),(4,5,6)]
    p = mp.Process(target=foo, args=())
    p.start()
    print("started")
    p.join()
    print("joined")
    sys.stdin = stdin
