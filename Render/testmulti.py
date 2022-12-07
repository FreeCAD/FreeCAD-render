from concurrent.futures import ProcessPoolExecutor, wait
import multiprocessing as mp
import sys

def f(verts):
    res = ["v {} {} {}".format(*v) for v in verts]
    assert 1==0
    print(res)

def f2(vert):
    return "v {} {} {}\n".format(*vert)

def foo(q):
    print("HERE3")
    print("foo name", __name__)
    for i in range(2):
        pass
    q.put('hello')

print("HERE2")
print("Module name", __name__)


if __name__ == 'builtins':
    mp.set_executable(sys.executable + " --console")
    stdin = sys.stdin
    sys.stdin = sys.__stdin__
    vertices = [(1,2,3),(4,5,6)]
    q1 = mp.Queue()
    p1 = mp.Process(target=foo, args=(q1,))
    p1.start()
    q2 = mp.Queue()
    p2 = mp.Process(target=foo, args=(q2,))
    p2.start()
    print(q1.get())
    p1.join()
    print(q2.get())
    p2.join()
    sys.stdin = stdin

    # print("HERE")
    # mp.set_executable("/usr/bin/python")
    # vertices = [(1,2,3),(4,5,6)]
    # q = mp.Queue()
    # p = mp.Process(target=foo, args=(q,))
    # p.start()
    # print(q.get())
    # p.join()
    # multiprocessing.set_executable("/usr/bin/python")
    # print(sys.executable)
    # print(sys.argv[0])
    # print("HERE2")
    # vertices = [(1,2,3),(4,5,6)]
    # with ProcessPoolExecutor(max_workers=1) as executor:
        # it = executor.map(f2, vertices)
        # for i in it:
            # print(i)
