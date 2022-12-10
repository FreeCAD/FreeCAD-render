import multiprocessing as mp


def foo(v):
    return "v {} {} {}\n".format(*v)



if __name__ == '__main__':
    import sys
    import os
    import shutil

    print("Entering main")

    # Set directory and stdout
    save_dir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    # Set executable
    executable = shutil.which("python")
    if not executable:
        raise RuntimeError("No Python executable")
    mp.set_executable(executable)
    mp.set_start_method('spawn', force=True)

    # Get variable
    try:
        vertices
    except NameError:
        vertices = [(1,2,3),(4,5,6)]

    res = []
    try:
        with mp.Pool() as pool:
            res = pool.map(foo, vertices)
            print(res)
    finally:
        os.chdir(save_dir)
