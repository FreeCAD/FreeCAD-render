import multiprocessing as mp
import functools

# Init
def init(*args):
    global fmt_v, fmt_vt, fmt_f, join_f, mask_f
    fmt_v = functools.partial(str.format, "v {} {} {}\n")
    fmt_vt = functools.partial(str.format, "vt {} {}\n")
    mask_f, *_ = args
    fmt_f = functools.partial(str.format, mask_f)
    join_f = functools.partial(str.join, "")

# Vertices
def func_v(val):
    return fmt_v(*val)

# UV map
def func_vt(val):
    return fmt_vt(*val)

# Faces
def func_f(val):
    return join_f(["f"] + [fmt_f(x + 1) for x in val] + ["\n"])

# String
def func_s(val):
    return val

# Main

if __name__ == '__main__':
    import sys
    import os
    import shutil
    import itertools

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
        inlist
    except NameError:
        inlist = [([(1,2,3)] * 2000000, "v")]  # Debug purpose

    try:
        mask
    except NameError:
        mask = ""

    try:
        objfile
    except NameError:
        objfile = "tmp.obj"

    # Parse format
    functions = {
        "v": func_v,
        "vt": func_vt,
        "f": func_f,
        "s": func_s,
    }

    chunk_size = 20000

    # Run
    try:
        with mp.Pool(processes=os.cpu_count(), initializer=init, initargs=(mask,)) as pool:
            result = (pool.imap(functions[fmt], values, chunk_size) for values, fmt in inlist)
            result = itertools.chain.from_iterable(result)
            with open(objfile, "w", encoding="utf-8") as f:
                f.writelines(result)
    finally:
        os.chdir(save_dir)
