import multiprocessing as mp
import functools

# Vertices

def init_v(args):
    global fmt_v
    fmt_v = functools.partial(str.format, "v {} {} {}\n")

def func_v(v):
    return fmt_v(*v)

# UV map

def init_vt(args):
    global fmt_vt
    fmt_vt = functools.partial(str.format, "vt {} {}\n")

def func_vt(v):
    return fmt_vt(*v)

# Faces

def init_f(*args):
    global fmt_f, join_f, mask_f
    mask_f = args[0]
    print("mask_f", mask_f)
    fmt_f = functools.partial(str.format, mask_f)
    join_f = functools.partial(str.join, "")

def func_f(v):
    return join_f(["f"] + [fmt_f(x + 1) for x in v] + ["\n"])

# Main

if __name__ == '__main__':
    import sys
    import os
    import shutil
    try:
        import FreeCAD as App
        debug = App.Console.PrintLog
    except ModuleNotFoundError:
        debug = print

    debug("[Render][Export] Using multiprocessing...\n")

    # Set directory and stdout
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set executable
    executable = shutil.which("python")
    if not executable:
        raise RuntimeError("No Python executable")
    mp.set_executable(executable)
    mp.set_start_method('spawn', force=True)

    # Get variables
    try:
        values
    except NameError:
        values = [(1,2,3),(4,5,6)]

    try:
        fmt
    except NameError:
        fmt = "v"

    try:
        length
    except NameError:
        length = 2

    try:
        mask
    except NameError:
        mask = ""

    # Parse format
    if fmt == "v":
        func, init = func_v, init_v
    elif fmt == "vt":
        func, init = func_vt, init_vt
    elif fmt == "f":
        func, init = func_f, init_f
    else:
        raise NotImplementedError(fmt)

    # Run
    result = []
    try:
        with mp.Pool(processes=4, initializer=init, initargs=(mask,)) as pool:
            result = pool.imap(func, values, 200)
            result = list(result)
    finally:
        os.chdir(save_dir)
