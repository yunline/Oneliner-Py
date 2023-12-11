# type: ignore
print("=== Return None by default 1 ===")


def func():
    pass


print(func())

print("=== Return None by default 2 ===")


def func():
    return


print(func())


print("=== Return directly ===")


def func():
    return 34567


print(func())

print("=== Return from If ===")


def func(a, b):
    if a:
        return 12345
    if b:
        return 34567
    if 1:
        print("hello")
        return 114514


for a, b in [(0, 0), (1, 0), (0, 1), (1, 1)]:
    print(func(a, b))

print("=== Return from If-Else ===")


def func(a, b):
    if a:
        pass
    else:
        return 12345
    if b:
        pass
    else:
        return 34567
    print("hello")


for a, b in [(0, 0), (1, 0), (0, 1), (1, 1)]:
    print(func(a, b))

print("=== Return from For loop ===")


def func():
    for _ in range(10):
        for __ in range(10):
            return 34567
        print("this should never print")


print(func())

print("=== Return from For-Else ===")


def func():
    for _ in []:
        pass
    else:
        return 34567


print(func())

print("=== Return from While loop ===")


def func():
    while 1:
        while 1:
            return 34567
        print("this should never print")


print(func())

print("=== Return from While-Else ===")


def func():
    while 0:
        pass
    else:
        return 34567


print(func())
