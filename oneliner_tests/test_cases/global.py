a = 0


def func1():
    global a
    a = 1


def func2():
    global a
    if (a := 3) == 3:
        print("xd")


def func3():
    a = 5


print(a)
func1()
print(a)
func2()
print(a)
func3()
print(a)

b = 0
c = 0


class B:
    global b
    b = 2
    c = 2


print(b)
print(c)
