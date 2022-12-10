import multiprocessing as mp


def fmt_v(v):
    print(globals())
    return "v {} {} {}\n".format(*v)


def fmt_vt(v):
    print(globals())
    return "vt {} {}\n".format(*v)

def init(args):
    global fmt_func
    fmt_func = args[0]

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

    if fmt == "v":
        func = fmt_v
    elif fmt == "vt":
        func = fmt_vt
    else:
        raise NotImplementedError(fmt)
    print(fmt)

    # Run
    result = []
    try:
        with mp.Pool(processes=4, initializer=init, initargs=(fmt,)) as pool:
            result = pool.imap(func, values, length // 4 + 1)
            result = list(result)
    finally:
        os.chdir(save_dir)
