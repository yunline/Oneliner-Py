# Test if the namespace of comprehension expr is isolated
# type: ignore


def func():
    i = 0

    def func2():
        nonlocal i
        i = 2
        [print(i) for i in range(10)]  # listcomp
        list(print(i) for i in range(10))  # genexpr
        {print(i) for i in range(10)}  # setcomp
        {print(i): None for i in range(10)}  # dictcomp

    func2()
    print(i)


func()


def func():
    i = 0

    def func2():
        nonlocal i
        i = 2

    class Foo:
        nonlocal i
        # test: comp inside a class
        [print(i) for i in range(10)]

    print(i)


func()


def func():
    i, j, k, m = 0, 0, 0, 0

    def func2():
        nonlocal i, j, k, m
        i, j, k, m = 9, 9, 9, 9
        lst = [(1, (2, 3)), (6, (7, 8))]

        # test: multi generator + tuple target
        [print(m, k, j, i) for (i, (j, k)) in lst for m in range(4)]

    func2()
    print(m, k, j, i)


func()


def func():
    i, j, k = 0, 0, 0

    def func2():
        nonlocal i, j, k
        i, j, k = 9, 9, 9

        # test: nested comp
        [
            [
                print(i),
                [
                    [
                        print(j),
                        [print(k) for k in range(4)],
                    ]
                    for j in range(4)
                ],
            ]
            for i in range(4)
        ]

    func2()
    print(k, j, i)


func()
