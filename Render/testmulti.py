import multiprocessing as mp


def foo():
    print("Entering foo")
    for i in range(2):
        pass


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

    try:
        p = mp.Process(target=foo, args=())
        p.start()
        print("started")
        p.join()
        print("joined")
    finally:
        os.chdir(save_dir)
