# type: ignore

b = 123


def func():
    a = 666

    def func3():
        def func4():
            print(a)
            print(b)

        func4()

    def func2():
        nonlocal a
        a = 1

    func3()
    func2()
    print(a)


func()


def func():
    d = 0

    class Foo:
        nonlocal d
        d = 12345

    foo = Foo()
    print(d)
    print(hasattr(foo, "d"))


func()


def func():
    d = 0

    class Foo:
        nonlocal d
        d = 12345

    class Foo2:
        print(d)


func()


def func():
    d = 0

    class Foo:
        d = 12345

        def meth(self):
            nonlocal d
            d = 54321

    foo = Foo()
    foo.meth()
    print(d)
    print(foo.d)


func()


def func():
    d = 0

    class Foo:
        d = 12345

        def meth(self):
            print(d)

    class Foo2:
        d = 23333

        class Foo3:
            nonlocal d
            d = 54321

        print(d)

    foo = Foo()
    foo.meth()
    print(foo.d)


func()


def func():
    a = 0

    # test function and lambda in one line
    def func2(arg=lambda a: None):
        nonlocal a
        a = 1

    func2()
    print(a)


func()


def func(arg):
    print(arg)

    def func2():
        nonlocal arg
        arg = 4

    func2()
    print(arg)


func(0)


def func(arg):
    class Foo:
        def meth(self):
            print(arg)

    def func2():
        nonlocal arg
        arg = 2

    Foo().meth()
    func2()
    Foo().meth()


func(0)
